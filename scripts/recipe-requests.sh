#!/bin/bash

set -euo pipefail;

declare CORE_URL="http://127.0.0.1:8000";

IFS=$'\n';

while true; do
	declare -a data=( $(curl "$CORE_URL/requestedRecipes" 2> /dev/null | jq -c '.[]') ) || {
		echo "Error: failed to get data from Core." >&2;

		exit 1;
	}

	if [ "${#data[@]}" -eq 0 ]; then
		echo "No requested recipes."

		exit 0;
	fi;

	declare num=0;

	for recipe in "${data[@]}";do
		let "num+=1";

		echo -n "$num: ";
		echo "$recipe" | jq "\"\(.name)@\(.version)\"" -r;
	done;

	echo "q. Quit";

	read num;

	if [ "$num" = "q" -o "$num" = "Q" ]; then
		exit 0;
	fi;
	
	if [ "$num" -gt 0 -a "$num" -le "${#data[@]}" ] 2> /dev/null; then
		while true; do
			echo "${data[$((num - 1))]}" | jq "\"\(.name)@\(.version)\\nUsername: \(.username)\\nURL: \(.url)\\nDescription: \(.description)\"" -r;

			echo -e "F. Fufill Request\nR. Remove Request\nB. Back";

			read v;

			case "$v" in
			"f"|"F")
				echo -n "Enter new package name (blank to keep existing): ";

				read pkgname;

				echo -n "Enter new package version (blank to keep existing): ";

				read pkgversion

				if curl -d "$({
					echo "${data[$((num - 1))]}" | jq '{"requestedName": .name, "requestedVersion": .version}' -c;
					echo "${data[$((num - 1))]}" | jq '{"name","version"}' -c;
					echo -e "$pkgname\n$pkgversion" | jq -s -R 'split("\n")[:2] | to_entries | map({(if .key == 0 then "name" else "version" end): .value}) | add | del(..|select(. == ""))' -c;
				} | jq -s add -c)" "$CORE_URL/fulfilRequestedRecipe"; then
					echo;

					break;
				fi;;
			"r"|"R")
				echo -n "Are you sure you want to remove the request $(echo "${data[$((num - 1))]}" | jq "\"\(.name)@\(.version)\"" -r)? (yN): ";

				read v;

				if [ "$v" = "y" -o "$v" = "Y" ]; then
					if curl -d "$(echo "${data[$((num - 1))]}" | jq 'with_entries(select([.key] | inside(["name", "version"])))')" "$CORE_URL/removeRequestedRecipe"; then
						echo;

						break;
					fi;
				else
					echo "Invalid Response.";
				fi;;
			"b"|"B")
				break;;
			*)
				echo "Invalid Response.";;
			esac;
		done;

	else
		echo "Invalid Response."
	fi;
done;
