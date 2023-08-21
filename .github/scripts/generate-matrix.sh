event_name="$1"
branch_name="$2"

if [[ "$event_name" == "workflow_dispatch" ]] || [[ "$branch_name" == "master" ]]; then
    echo '{
      "python-version": ["3.8", "3.9", "3.10", "3.11"],
      "os": ["ubuntu-latest", "macos-latest"],
      "borg-version": ["1.2.4"]
    }' | jq -c . > matrix-unit.json

    echo '{
      "python-version": ["3.8", "3.9", "3.10", "3.11"],
      "os": ["ubuntu-latest", "macos-latest"],
      "borg-version": ["1.1.18", "1.2.2", "1.2.4", "2.0.0b5"],
      "exclude": [{"borg-version": "2.0.0b5", "python-version": "3.8"}]
    }' | jq -c . > matrix-integration.json

elif [[ "$event_name" == "push" ]] || [[ "$event_name" == "pull_request" ]]; then
    echo '{
      "python-version": ["3.8", "3.9", "3.10", "3.11"],
      "os": ["ubuntu-latest", "macos-latest"],
      "borg-version": ["1.2.4"]
    }' | jq -c . > matrix-unit.json

    echo '{
      "python-version": ["3.10"],
      "os": ["ubuntu-latest"],
      "borg-version": ["1.2.4"]
    }' | jq -c . > matrix-integration.json
fi
