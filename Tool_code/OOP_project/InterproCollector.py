import sys, errno, re, json, ssl, os
from urllib import request
from urllib.error import HTTPError
from time import sleep
import pandas as pd
from Director import SourceBuilder


class InterProBuilder(SourceBuilder):
    def __init__(self):
        self.savePath = os.getcwd() + '/data/'
        self.BASE_URL = "https://www.ebi.ac.uk:443/interpro/api/entry/InterPro/?page_size=100"
        self.outputFile = self.savePath + "InterPro_entries.txt"

    def downloader(self):
        # def output_list():
        # disable SSL verification to avoid config issues
        context = ssl._create_unverified_context()

        next = self.BASE_URL
        last_page = False

        f = open(self.outputFile, "w")
        sys.stdout = f
        #fieldnames = ['Accession', 'Name', 'SourceDatabase', 'Type', 'IntegratedSignatures',
        #              'GOTerms']
        delimiter = "|"
        #sys.stdout.write(delimiter.join(fieldnames))
        #sys.stdout.write("\n")
        # writer = csv.writer(f, delimiter='|')
        # writer.writerow(fieldnames)
        while next:
            try:
                req = request.Request(next, headers={"Accept": "application/json"})
                res = request.urlopen(req, context=context)
                # If the API times out due a long running query
                if res.status == 408:
                    # wait just over a minute
                    sleep(61)
                    # then continue this loop with the same URL
                    continue
                elif res.status == 204:
                    # no data so leave loop
                    break
                payload = json.loads(res.read().decode())
                next = payload["next"]
                if not next:
                    last_page = True
            except HTTPError as e:
                if e.code == 408:
                    sleep(61)
                    continue
                else:
                    raise e

            for i, item in enumerate(payload["results"]):
                # writer.writerow([parse_column(item["metadata"]["accession"], 'metadata.accession'),
                #                 parse_column(item["metadata"]["name"], 'metadata.name'),
                #                 parse_column(item["metadata"]["source_database"], 'metadata.source_database'),
                #                 parse_column(item["metadata"]["type"], 'metadata.type'),
                #                 parse_column(item["metadata"]["member_databases"], 'metadata.member_databases'),
                #                 parse_column(item["metadata"]["go_terms"], 'metadata.go_terms')])
                sys.stdout.write(parse_column(item["metadata"]["accession"], 'metadata.accession') + delimiter)
                sys.stdout.write(parse_column(item["metadata"]["name"], 'metadata.name') + delimiter)
                sys.stdout.write(
                    parse_column(item["metadata"]["source_database"], 'metadata.source_database') + delimiter)
                sys.stdout.write(parse_column(item["metadata"]["type"], 'metadata.type') + delimiter)
                # sys.stdout.write(parse_column(item["metadata"]["integrated"], 'metadata.integrated') + ",")
                sys.stdout.write(
                    parse_column(item["metadata"]["member_databases"], 'metadata.member_databases') + delimiter)
                sys.stdout.write(parse_column(item["metadata"]["go_terms"], 'metadata.go_terms') + delimiter)
                sys.stdout.write("\n")

                # Don't overload the server, give it time before asking for more
            if next:
                sleep(1)
        f.close()

    def parser(self):
        # self.outputFile
        myf = r"C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP\Tool_code\OOP_project\data\InterPro_entries.txt"


def parse_items(items):
    if type(items) == list:
        return ",".join(items)
    return ""


def parse_member_databases(dbs):
    if type(dbs) == dict:
        return ";".join([f"{db}:{','.join(dbs[db])}" for db in dbs.keys()])
    return ""


def parse_go_terms(gos):
    if type(gos) == list:
        return ",".join([go["identifier"] for go in gos])
    return ""


def parse_locations(locations):
    if type(locations) == list:
        return ",".join(
            [",".join([f"{fragment['start']}..{fragment['end']}"
                       for fragment in location["fragments"]
                       ])
             for location in locations
             ])
    return ""


def parse_group_column(values, selector):
    return ",".join([parse_column(value, selector) for value in values])


def parse_column(value, selector):
    if value is None:
        return ""
    elif "member_databases" in selector:
        return parse_member_databases(value)
    elif "go_terms" in selector:
        return parse_go_terms(value)
    elif "children" in selector:
        return parse_items(value)
    elif "locations" in selector:
        return parse_locations(value)
    return str(value)

if __name__ == "__main__":
    inter = InterProBuilder()
    inter.downloader()