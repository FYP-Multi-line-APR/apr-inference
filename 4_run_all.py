import os
import subprocess
# Specify the root directory where your directories (Chart, Cli, etc.) are located
root_directory = './defects4j-setup/train-data/'
data = {
    'Chart': [14, 16],
    'Closure': [4, 78, 79, 106, 109, 115, 131],
    'Lang': [7, 27, 34, 35, 41, 47, 60],
    'Math': [1, 4, 22, 24, 35, 43, 46, 62, 65, 71, 77, 79, 88, 90, 93, 98, 99]
}

# Iterate over each directory in the root directory
for project_name in data.keys():
    # Construct the full path of the project directory
    project_directory = os.path.join(root_directory, project_name)

    # Check if the item in the root directory is a directory
    # if os.path.isdir(project_directory):
        # Iterate over the files in the project directory
    for filename in data[project_name]:
        filename = str(filename) + ".json"
        # Check if the file is a JSON file
        if filename.endswith('.json'):
            # Extract the project name and filename
            a =project_name
            b=filename[:-5]
            print(f"Project Name: {project_name}, Filename: {filename[:-5]}")
            command = f"python3 1_localize_fault.py {a} {b} init"
            
            # Execute the command
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            # Print the output of the script
            print(result.stdout)
            print(result.stderr)
            command = f"python3 2_make_test_sample.py {a} {b}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            print(result.stdout)
            print(result.stderr)

            command = f"python3 3_repair.py {a} {b}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            print(result.stdout)
            print(result.stderr)
            print("\n\n\n\n\n")
            
            break
