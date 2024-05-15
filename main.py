#!/usr/bin/env python3

import requests
import json
import os
import argparse

from LegacyVersion import LegacyVersion
from collections import defaultdict


class ApiAltRepo:
    def __init__(self):
        self.base_url = "https://rdb.altlinux.org/api/export/branch_binary_packages/"
        self.branch_p10 = "p10"
        self.branch_sisyphus = "sisyphus"

    def main(self, use_cache: bool = True) -> None:
        p10 = self.get_packages(self.branch_p10, use_cache)
        sisyphus = self.get_packages(self.branch_sisyphus, use_cache)
        uniq_p10, uniq_sisyphus = self.uniq_by_arch(p10, sisyphus)
        version_release_by_arch_more_sisyphus = self.version_release_by_arch_more_sisyphus(p10, sisyphus)

        data = {
            "uniq_p10": uniq_p10,
            "uniq_sisyphus": uniq_sisyphus,
            "version_release_by_arch_more_sisyphus": version_release_by_arch_more_sisyphus,
        }

        print(json.dumps(data, indent=1))

    def get_packages(self, branch: str, use_cache: bool = True) -> json:
        print(f"requesting {branch}")
        path = f"{branch}.json"

        if use_cache and os.path.exists(path):
            print(f"cache hit {branch}")
            with open(path) as f:
                return json.load(f)

        url = f"{self.base_url}{branch}"
        response = requests.get(url=url)
        print(f"{branch} {response.status_code}")

        if response.status_code == 200:
            resp_json = response.json()
            with open(f"{branch}.json", "w") as f:
                json.dump(resp_json, f)
                print(f"dumped {branch}")
                return resp_json

        raise ValueError(f"{response.status_code=}")

    @staticmethod
    def uniq_by_arch(p10: json, sisyphus: json) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        arches = {item["arch"] for item in p10["packages"]} | {item["arch"] for item in sisyphus["packages"]}
        packages_p10 = defaultdict(set)
        packages_sisyphus = defaultdict(set)

        for item in p10["packages"]:
            packages_p10[item["arch"]].add(item["name"])

        for item in sisyphus["packages"]:
            packages_sisyphus[item["arch"]].add(item["name"])

        uniq_p10 = {
            arch: list(packages_p10[arch] - packages_sisyphus[arch]) for arch in arches
        }
        uniq_sisyphus = {
            arch: list(packages_sisyphus[arch] - packages_p10[arch]) for arch in arches
        }

        return uniq_p10, uniq_sisyphus

    @staticmethod
    def version_release_by_arch_more_sisyphus(p10: json, sisyphus: json) -> dict[str, list[str]]:
        result_map_p10 = defaultdict(dict)
        result_map_sisyphus = defaultdict(dict)

        for item in sisyphus["packages"]:
            result_map_sisyphus[item["arch"]][item["name"]] = f"{item['epoch']}:{item['version']}-{item['release']}"

        for item in p10["packages"]:
            result_map_p10[item["arch"]][item["name"]] = f"{item['epoch']}:{item['version']}-{item['release']}"

        result = defaultdict(list)

        for arch, packages in result_map_sisyphus.items():
            for package, sisyphus_version_release in packages.items():
                if arch in result_map_p10 and package in result_map_p10[arch]:
                    p10_version_release = result_map_p10[arch][package]

                    sisyphus_version_object = LegacyVersion(sisyphus_version_release)
                    p10_version_object = LegacyVersion(p10_version_release)

                    if sisyphus_version_object > p10_version_object:
                        result[arch].append(package)

        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='main.py')
    parser.add_argument('--no-cache',
                        dest='use_cache',
                        action='store_false',
                        help='Disable cache')

    args = parser.parse_args()
    api = ApiAltRepo()

    api.main(args.use_cache)
