#     CT SDE EdSight Data Scraping Command Line Interface.
#     Copyright (C) 2017  Sasha Cuerda, Connecticut Data Collaborative
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
from urllib.parse import urlparse, parse_qs
from itertools import product
from slugify import Slugify

custom_slugify = Slugify(to_lower=True)
custom_slugify.safe_chars = '_'

HEADERS = {
    'user-agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/45.0.2454.101 Safari/537.36'),
}

def _state_enrollment_url_list(output_dir):
    """One off method for dealing with non-standard format of state-level enrollment data"""
    var_map = {
        '1': 'grade-by-gender',
        '2': 'race_ethnicity-by-gender',
        '3': 'race_ethnicity-by-special-education',
        '4': 'race_ethnicity-by-ell',
        '5': 'race_ethnicity-by-free_reduced_lunch'
    }

    years = [
        '2007-08', '2008-09', '2009-10', '2010-11', '2011-12',
        '2012-13', '2013-14', '2014-15', '2015-16', '2016-17'
    ]

    urls = []
    for year in years:
        for key, val in var_map.items():
            url = f'http://edsight.ct.gov/SASStoredProcess/do?_program=/CTDOE/EdSight/Release/Reporting/Public/Reports/StoredProcesses//EnrollmentYearExport&_year={year}&_district=State+of+Connecticut&_school=+&_subgroup=+&display={key}'
            filename = f'enrollment__{year}_{val}_ct.csv'
            full_output_path = os.path.join(os.path.abspath(output_dir), filename)
            urls.append({'url': url, 'param': {}, 'filename': full_output_path})

    trend_subgroups = [
        'All+Students',
        'Race',
        'Gender',
        'Lunch',
        'Special+Education',
        'ELL'
    ]

    for group in trend_subgroups:
        url = f'http://edsight.ct.gov/SASStoredProcess/do?_program=/CTDOE/EdSight/Release/Reporting/Public/Reports/StoredProcesses//EnrollmentTrendExport&_year=Trend&_district=State+of+Connecticut&_school=+&_subgroup={group}'
        filename = f'enrollment__trend_{group.lower().replace("+", "-")}_ct.csv'
        full_output_path = os.path.join(os.path.abspath(output_dir), filename)
        urls.append({'url': url, 'param': {}, 'filename': full_output_path})

    return urls

    # [{'url': 'http://edsight.ct.gov/do', 'param': {'_year': 'Trend', '_subgroup': 'All Students'},
    #   'filename': './test_Trend_All-Students.csv'},
    #  {'url': 'http://edsight.ct.gov/do', 'param': {'_year': 'Trend', '_subgroup': 'Race/Ethnicity'},
    #   'filename': './test_Trend_Race-Ethnicity.csv'},
    #  {'url': 'http://edsight.ct.gov/do', 'param': {'_year': '2015-16', '_subgroup': 'All Students'},
    #   'filename': './test_2015-16_All-Students.csv'},
    #  {'url': 'http://edsight.ct.gov/do', 'param': {'_year': '2015-16', '_subgroup': 'Race/Ethnicity'},
    #   'filename': './test_2015-16_Race-Ethnicity.csv'}]


def _build_catalog_geo_list(catalog):
    dirs = []
    for k,v in catalog.items():
        dirs.append(
            {
                'dataset': k,
                'geos': [g['name'] for g in v['filters'] if g['name'] in ['District', 'School']]
            })
    return dirs


def _build_params_list(dataset, base_qs, variables):
    filters = list(product(*[f['options'] for f in dataset['filters'] if f['name'] in variables]))
    param_options = [f['xpath_id'] for f in dataset['filters'] if f['name'] in variables]
    params = []
    for i, f in enumerate(filters):
        new_qs = {**base_qs}
        for idx, p in enumerate(param_options):
            # We use rstrip here b/c there is a lack of consistency within edsight for how params values
            # are listed in the dropdown markup and how the export csv wants to receive that param.
            # An extra space in a param value appears to cause edsight to dump a wider range of data than
            # is being asked for.
            new_qs[p] = f[idx].rstrip()
        for k,v in new_qs.items():
            if not isinstance(v, str):
                new_qs[k] = v[0]
        params.append(new_qs)
    return params

def _get_xpaths(filters, variables):
    return [f['xpath_id'] for f in filters if f['name'] in variables]


def _build_url_list(params, xpaths, url, output_dir, dataset_name):
    """Build up a list of target objects."""
    targets = []
    for p in params:
        # In testing we have a basic param object, but in actual work it is more complex
        # and includes params that are only specific to the SAS stored procedure. We don't need
        # these for the file naming, which is why we use the xpath lookup to pull out the subset
        f = [p.get(v,'') for v in xpaths]
        if p['_district'] == 'State of Connecticut':
            f.append('ct')
        filename_variables = '_'.join(f)
        filename = "{}__{}".format(dataset_name, filename_variables)
        slugged_filename = "{}.csv".format(custom_slugify(filename))
        full_output_path = os.path.join(os.path.abspath(output_dir), slugged_filename)
        targets.append({'url': url, 'param': p, 'filename': full_output_path})

    if dataset_name == 'Enrollment':
        state_enrollment = _state_enrollment_url_list(output_dir)
        targets.extend(state_enrollment)

    return targets

def _add_ct(param_list):
    ct_list = []
    for p in param_list:
        new = {**p}
        new['_district'] = 'State of Connecticut'
        if '_school' in new:
            new.__delitem__('_school')
        if new not in ct_list:
            ct_list.append(new)
    return param_list + list(ct_list)


def _setup_download_targets(dataset, output_dir, geography, catalog):
    """Prepares a list of dictionaries which contain the components needed to generate a request and save results.
     
     Return object looks similar to this:
     
     [{'url': 'http://edsight.ct.gov/do', 'param': {'_year': 'Trend', '_subgroup': 'All Students'},
        'filename': './test_Trend_All-Students.csv'},
       {'url': 'http://edsight.ct.gov/do', 'param': {'_year': 'Trend', '_subgroup': 'Race/Ethnicity'},
        'filename': './test_Trend_Race-Ethnicity.csv'},
       {'url': 'http://edsight.ct.gov/do', 'param': {'_year': '2015-16', '_subgroup': 'All Students'},
        'filename': './test_2015-16_All-Students.csv'},
       {'url': 'http://edsight.ct.gov/do', 'param': {'_year': '2015-16', '_subgroup': 'Race/Ethnicity'},
        'filename': './test_2015-16_Race-Ethnicity.csv'}]
    """
    ds = catalog[dataset]
    ds_filters = ds['filters']
    dl_link = ds['download_link']

    if geography == 'District':
        exclude_vars = ['District', 'School']
    elif geography == 'School':
        exclude_vars = ['District']

    variable = [x.get('name') for x in ds_filters if x.get('name') not in exclude_vars]

    # Parse the link url, extract the basic params and then reset the url to its root
    dl_parsed = urlparse(dl_link)
    qs = parse_qs(dl_parsed.query)
    new_url = dl_parsed._replace(query=None).geturl()

    # Call helper function to extract the correct xpaths from our lookup
    xpaths = _get_xpaths(ds_filters, variable)

    # Build up a list params for each variable combo
    params = _build_params_list(ds, qs, variable)
    if dataset != 'Enrollment':
        params = _add_ct(params)
    # Return a list of objects that can be past to our http request
    # generator to build up a final url with params

    return _build_url_list(params, xpaths, new_url, output_dir, dataset)
