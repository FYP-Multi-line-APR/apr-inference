#!/bin/bash

# Check if the project directory is provided as a command-line argument
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <project_directory>"
  exit 1
fi

# Get the project directory from the command-line argument
project_dir="$1"

# Check if the provided directory exists
if [ ! -d "$project_dir" ]; then
  echo "Error: Directory '$project_dir' not found."
  exit 1
fi

echo "Current path: $(pwd)"

# Change to the project directory
cd "$project_dir" || exit 1

echo "Current path: $(pwd)"

# Run Maven clean and compile goals, capturing the output
output=$(mvn clean compile 2>&1)

# Check if the compilation was successful
if [ $? -eq 0 ]; then
  echo "Compilation successful."
else
  echo "Compilation failed. Printing errors..."

  # Print compilation errors
  echo "$output" | grep "ERROR"
fi
