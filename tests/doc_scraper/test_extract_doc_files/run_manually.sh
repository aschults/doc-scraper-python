#!/bin/bash
set -e -x

script_dir=$(dirname "$0")

if [ "${script_dir#/}" = "${script_dir}" ] ; then
    # Not starting with /
    script_dir="$(pwd)/${script_dir}"
fi

base_dir="${script_dir}/../../.."

cd "${script_dir}/$1"

export PYTHONPATH="${base_dir}" 
python3 "${base_dir}/doc_scraper/extract_doc.py" --config=config.yaml <data.html