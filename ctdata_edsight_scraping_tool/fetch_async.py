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
import time
import asyncio
import aiofiles
import aiohttp

from .helpers import _setup_download_targets

sema = asyncio.BoundedSemaphore(10)

BASE_URL = 'http://edsight.ct.gov/SASPortal/main.do'
HEADERS = {
    'user-agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/45.0.2454.101 Safari/537.36'),
}

async def get_report(url, params, file, save):
    async with sema:
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL, headers=HEADERS) as context:
                pass
            data = '<html>'
            tries = 0
            target_url = ''
            while tries < 4 and data.find('<html>') != -1:
                if tries > 0:
                    print("Try #{} for fetching {}".format(tries, target_url))
                    time.sleep(.75)
                async with session.get(url, headers=HEADERS, params=params) as resp:
                    data = await resp.text()
                    target_url = resp.url
                tries += 1
            if save:
                if data.find('The query you have run did not contain any results.') == -1 and data.find('<html>') == -1:
                    async with aiofiles.open(file, 'w') as f:
                        print('Saving {}\n'.format(os.path.basename(file)))
                        await f.write(data)
                else:
                    print("{} failed.".format(target_url))


def fetch_async(dataset, output_dir, geography, catalog, save=True):
    targets = _setup_download_targets(dataset, output_dir, geography, catalog)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        asyncio.gather(
            *(get_report(t['url'], t['param'], t['filename'], save) for t in targets)
        )
    )
