#!/usr/bin/env bash


operation="$1"

if [ "$operation" = "" ]; then
    echo -e "\n$(tput setaf 10)Error! Need operation as parameter.$(tput sgr 0)"
    exit 5
fi

for node in `virsh list --all|egrep -v '\-\-\-|Id'|awk '{print $2}'`
do
    virsh $operation $node
done