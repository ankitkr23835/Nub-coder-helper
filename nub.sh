#!/bin/bash

python3 -m venv venv
source venv/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt
#!/bin/bash

# Define an array of process names and their corresponding commands
declare -A processes
processes["zipper.py"]="nohup python3 main.py &"
# Declare an associative array to track process PIDs
declare -A pids

# Monitor and restart processes
while true; do
    for process_name in "${!processes[@]}"; do
        # Get the PID of the process
        pid="${pids[$process_name]}"

        if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
            python3 -m venv venv
            pip3 install --upgrade pip
            pip3 install -r requirements.txt
            echo "Starting $process_name..."
            eval "${processes[$process_name]}"
            # Store the PID of the newly started process
            pids["$process_name"]="$!"
        fi
    done
    sleep 60
done

