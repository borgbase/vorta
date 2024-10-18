event_name="$1"
branch_name="$2"

if [[ "$event_name" == "workflow_dispatch" ]] || [[ "$branch_name" == "master" ]]; then
    echo '{
      "python-version": ["3.9", "3.10", "3.11", "3.12"],
      "os": ["ubuntu-22.04", "macos-14"],
      "borg-version": ["1.4.0"]
    }' | jq -c . > matrix-unit.json

    echo '{
      "python-version": ["3.11"],
      "os": ["ubuntu-22.04"],
      "borg-version": ["1.1.18", "1.2.8", "1.4.0", "2.0.0b12"],
      "exclude": [{"borg-version": "2.0.0b12", "python-version": "3.8"}]
    }' | jq -c . > matrix-integration.json

elif [[ "$event_name" == "push" ]] || [[ "$event_name" == "pull_request" ]]; then
    echo '{
      "python-version": ["3.9", "3.12"],
      "os": ["ubuntu-22.04", "macos-14"],
      "borg-version": ["1.2.8"]
    }' | jq -c . > matrix-unit.json

    echo '{
      "python-version": ["3.11"],
      "os": ["ubuntu-22.04"],
      "borg-version": ["1.2.8"]
    }' | jq -c . > matrix-integration.json
fi
