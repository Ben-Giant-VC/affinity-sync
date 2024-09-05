CURRENT_VERSION=$(pip index versions airtable-pg-sync | grep "airtable-pg-sync (" | awk '{print $2}' | tr -d '()')
NEW_VERSION=$(echo $CURRENT_VERSION | awk -F. '{$NF = $NF + 1;} 1' | sed 's/ /./g')
sed -i '' "s/<CURRENT_VERSION>/${NEW_VERSION}/g" pyproject.toml


