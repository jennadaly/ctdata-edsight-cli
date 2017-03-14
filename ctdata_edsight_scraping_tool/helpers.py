# -*- coding: utf-8 -*-
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


from urllib.parse import urlparse, parse_qs
from itertools import product


HEADERS = {
    'user-agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/45.0.2454.101 Safari/537.36'),
}



def _build_params_list(dataset, base_qs, variables):
    filters = list(product(*[f['options'] for f in dataset['filters'] if f['name'] in variables]))
    param_options = [f['xpath_id'] for f in dataset['filters'] if f['name'] in variables]
    params = []
    for i, f in enumerate(filters):
        new_qs = {**base_qs}
        for idx, p in enumerate(param_options):
            new_qs[p] = f[idx]
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
        f = [p[v] for v in xpaths]
        filename_variables = '_'.join(f)
        slug = filename_variables.replace('/', '-').replace(' ', '-')
        filename = "{}{}_{}.csv".format(output_dir, dataset_name, slug)
        targets.append({'url': url, 'param': p, 'filename': filename})
    return targets

def _setup_download_targets(dataset, output_dir, variable, catalog):
    """Download the csv file of the dataset to a target directory."""
    ds = catalog[dataset]
    ds_filters = ds['filters']
    dl_link = ds['download_link']

    # Parse the link url, extract the basic params and then reset the url to its root
    dl_parsed = urlparse(dl_link)
    qs = parse_qs(dl_parsed.query)
    new_url = dl_parsed._replace(query=None).geturl()

    # Call helper function to extract the correct xpaths from our lookup
    xpaths = _get_xpaths(ds_filters, variable)

    # Build up a list params for each variable combo
    params = _build_params_list(ds, qs, variable)

    # Return a list of objects that can be past to our http request
    # generator to build up a final url with params
    return _build_url_list(params, xpaths, new_url, output_dir, dataset)