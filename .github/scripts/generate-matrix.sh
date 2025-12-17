event_name="$1"
branch_name="$2"

if [[ "$event_name" == "workflow_dispatch" ]] || [[ "$branch_name" == "master" ]]; then
    echo '{
      "python-version": ["3.10", "3.12", "3.13"],
      "os": ["ubuntu-24.04", "macos-15"],
      "borg-version": ["1.4.3"]
    }' | jq -c . > matrix-unit.json

    echo '{
      "python-version": ["3.12"],
      "os": ["ubuntu-24.04"],
      "borg-version": ["1.2.8", "1.4.2"],
      "exclude": [{"borg-version": "2.0.0b12", "python-version": "3.8"}]
    }' | jq -c . > matrix-integration.json

elif [[ "$event_name" == "push" ]] || [[ "$event_name" == "pull_request" ]]; then
    echo '{
      "python-version": ["3.12"],
      "os": ["ubuntu-24.04", "macos-15"],
      "borg-version": ["1.2.8"]
    }' | jq -c . > matrix-unit.json

    echo '{
      "python-version": ["3.12"],
      "os": ["ubuntu-24.04"],
      "borg-version": ["1.4.2"]
    }' | jq -c . > matrix-integration.json
fi
