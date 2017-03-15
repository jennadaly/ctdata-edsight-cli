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

import json
import sys
import os

import click
import requests

from pkg_resources import resource_string

from .links_prep import rebuild

ASYNC_AVAILABLE = False

# Import sync or async version of fetching routine
if sys.version_info[0:2] >= (3, 5):
    from .fetch_async import fetch_async as fetcher
    from .fetch_sync import fetch_sync as fetcher_sync
    ASYNC_AVAILABLE = True
else:
    from .fetch_sync import fetch_sync as fetcher



BASE_URL = 'http://edsight.ct.gov/SASPortal/main.do'
HEADERS = {
    'user-agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/45.0.2454.101 Safari/537.36'),
}

# Get the etag from s3
s3_object = requests.head('https://s3.amazonaws.com/edsightcli/datasets.json')
etag = s3_object.headers.get('ETag').replace('"','')


LINKS_DIR = os.path.join(os.path.dirname(__file__), 'catalog')
LINKS_PATH = os.path.join(LINKS_DIR, '{}.json'.format(etag))

# Look for a file named using the etag. If it is missing, it means the catalog has changed and we need to update
if os.path.isfile(LINKS_PATH):
    click.echo("Dataset catalog is found!")
    links = json.loads(resource_string(__name__, 'catalog/{}.json'.format(etag)))
else:
    import json
    click.echo("Downloading the dataset catalog...")
    r = requests.get('https://s3.amazonaws.com/edsightcli/datasets.json')
    links = json.loads(r.content)
    if not os.path.isdir(LINKS_DIR):
        os.makedirs(LINKS_DIR)
    with open(LINKS_PATH, 'w') as f:
        json.dump(links, f)




@click.group()
def main(args=None):
    """Console script for ctdata_edsight_scraping_tool

    CTData EdSight CLI  Copyright (C) 2017  Connecticut Data Collaborative
    This program comes with ABSOLUTELY NO WARRANTY; for details type 'edsight warranty'.
    This is free software, and you are welcome to redistribute it
    under certain conditions; type `edsight conditions' for details.
    """

@main.command()
def curdir():
    click.echo(os.path.dirname(__file__))

@main.command()
def warranty():
    """Display GPL 3.0 warranty clause"""
    click.echo("""
    THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY
    APPLICABLE LAW.  EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT
    HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM "AS IS" WITHOUT WARRANTY
    OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO,
    THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
    PURPOSE.  THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM
    IS WITH YOU.  SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF
    ALL NECESSARY SERVICING, REPAIR OR CORRECTION.\n\n""")

@main.command()
def conditions():
    """Display GPL 3.0 abbreviated conditions of redistribution clause."""
    click.echo("""
      All rights granted under this License are granted for the term of
    copyright on the Program, and are irrevocable provided the stated
    conditions are met.  This License explicitly affirms your unlimited
    permission to run the unmodified Program.  The output from running a
    covered work is covered by this License only if the output, given its
    content, constitutes a covered work.  This License acknowledges your
    rights of fair use or other equivalent, as provided by copyright law.

      You may make, run and propagate covered works that you do not
    convey, without conditions so long as your license otherwise remains
    in force.  You may convey covered works to others for the sole purpose
    of having them make modifications exclusively for you, or provide you
    with facilities for running those works, provided that you comply with
    the terms of this License in conveying all material for which you do
    not control copyright.  Those thus making or running the covered works
    for you must do so exclusively on your behalf, under your direction
    and control, on terms that prohibit them from making any copies of
    your copyrighted material outside their relationship with you.

      Conveying under any other circumstances is permitted solely under
    the conditions stated in the full license.  Sublicensing is not allowed;
    section 10 makes it unnecessary.\n\n
    """)

@main.command()
@click.option('--async', '-a',
              is_flag=True,
              help="Use the faster, asynchronous download script if on Python 3.5+."
              )
@click.option('--dataset', '-d',
              required=True,
              help="Name of the dataset to retrieve. Should conform to names output by the info cmd.")
@click.option('--output_dir',
              '-o',
              required=True,
              help="Full or relative path for storing downloaded files.",
              default='./')
@click.option('--variable',
              '-v',
              required=True,
              multiple=True,
              help="Variable to fetch. Can be multiple in which case each combination will be fetched")
def fetch(dataset, output_dir, variable, async):
    """Download the csv file of the dataset to a target directory.

    On Python versions below 3.5, fetching can take a few minutes or more to complete. This because each dataset is
    requested in sequence. In Python 3.5 and 3.6, the data requests happen asynchronously which results in significant
    performance gains.
    """
    if not os.path.isdir(output_dir):
        raise NotADirectoryError("{} not a valid directory".format(output_dir))
    if async and ASYNC_AVAILABLE:
        fetcher(dataset, output_dir, variable, links)
    elif async and not ASYNC_AVAILABLE:
        click.echo("Sorry, but the async downloader is not available on your platform.")
        if click.confirm("Do you want to proceed with the default downloader?"):
            fetcher_sync(dataset, output_dir, variable, links, save=True)
    else:
        fetcher_sync(dataset, output_dir, variable, links, save=True)

@main.command()
@click.option('--target', '-t', required=True)
def refresh(target):
    """Update the dataset manifest file with a refreshed list of possible variables."""
    rebuild(links, target)

@main.command()
def datasets(args=None):
    """List datasets that are available for scraping"""
    for d in links.items():
        click.echo(d[0])

@main.command()
@click.option('--dataset', required=True,)
@click.option('--variable', required=False)
def info(dataset, variable):
    """Information about a dataset. Takes dataset name as an argument."""
    filters = links[dataset]['filters']
    if variable:
        var = [f for f in filters if f['name'] == variable][0]
        options = var['options']
        click.echo("\n`{}` has the following options available:\n".format(variable))
    else:
        options = [f['name'] for f in filters]
        click.echo("\n`{}` has the following variables available:\n".format(dataset))
    for o in options:
        click.echo("- {}".format(o))

if __name__ == "__main__":
    main()


def gen_resource(directory_name, dataset_name):
    datafiles = [f.replace("./", "./data/") for f in get_filepaths("./{}".format(directory_name)) if f.endswith(".csv")]
    r = {"name": dataset_name, "data": datafiles}
    return json.dumps(r)
