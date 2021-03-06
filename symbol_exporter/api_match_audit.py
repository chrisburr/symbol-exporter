import glob
import json
import os

import requests
from tqdm import tqdm

from symbol_exporter.api_match import find_supplying_version_set
from symbol_exporter.ast_db_populator import sort_arch_ordering

from random import shuffle


def main(n_to_pull=1000):
    if not os.path.exists("audit"):
        os.makedirs("audit")
    existing_artifacts = glob.glob("audit/**/*.json", recursive=True)
    existing_names = {k.partition("/")[2] for k in existing_artifacts}
    existing_pkg_names = {k.partition("/")[0] for k in existing_names}

    def not_already_audited(k):
        return k.partition("/")[2] not in existing_names

    artifacts = [
        k
        for k in requests.get(
            "https://raw.githubusercontent.com/symbol-management/ast-symbol-table/master/.file_listing.json"
        ).json()
        if k.startswith("symbols") and not_already_audited(k)
    ]
    # Don't have the artifacts in alphabetical order
    shuffle(artifacts)

    def diff_sort(val):
        _, package, channel, arch, name = val.split("/")
        return (
            package in existing_pkg_names,
            sort_arch_ordering.index(arch),
        )

    for i, artifact in tqdm(
        enumerate(sorted(artifacts, key=diff_sort)), total=n_to_pull
    ):
        if i >= n_to_pull:
            break
        print(artifact)
        symbols = requests.get(
            f"https://raw.githubusercontent.com/symbol-management/ast-symbol-table/master/{artifact}"
        ).json()
        if not symbols:
            continue
        volume = set()
        for v in symbols.values():
            volume.update(v.get("symbols_in_volume", set()))
        deps, bad = find_supplying_version_set(volume)
        dep_sets = [list(sorted(k)) for k in deps]

        outname = artifact.replace("symbols/", "audit/")
        os.makedirs(os.path.dirname(outname), exist_ok=True)
        with open(outname, "w") as f:
            json.dump(
                {"deps": dep_sets, "bad": list(sorted(bad))},
                f,
                indent=1,
                sort_keys=True,
            )


if __name__ == "__main__":
    main()
