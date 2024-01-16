#!/bin/bash

# Check if the path argument is provided
if [ -z "$1" ]; then
  echo "Error: Please provide the path to the Java project."
  exit 1
fi

# Navigate to the provided project path
cd "$1" || exit 1

# Print the current working directory
echo "Current path: $(pwd)"

# Run Maven clean and test goals
mvn clean test

# Check the exit status of the Maven test command
if [ $? -eq 0 ]; then
  echo "All tests passed successfully."
else
  echo "Some tests failed. Please check the test results."
fi
