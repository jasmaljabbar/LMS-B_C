#!/bin/bash
set -e

# Check if the argument is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <file_list>"
    exit 1
fi

# Define the input file from the argument
FILE_LIST="$1"
OUTPUT_FILE="context.txt"

# Check if the provided file exists
if [ ! -f "$FILE_LIST" ]; then
    echo "Error: File '$FILE_LIST' not found!"
    exit 1
fi

# Clear the output file before appending
> "$OUTPUT_FILE"

# Read each filename from the file and append its content
echo "Here is the context of the source tree and the files:" >> "$OUTPUT_FILE"
echo "Store the context. Based on the context, I will be asking questions later." >> "$OUTPUT_FILE"
echo "Wait for my questions before you provide any kind of response." >> "$OUTPUT_FILE"
echo "# Source Tree" >> "$OUTPUT_FILE"
tree -I '__pycache__|*.pyc' >> "$OUTPUT_FILE"

while IFS= read -r file; do
    if [ -f "$file" ]; then
        echo "" >> "$OUTPUT_FILE"
        echo "# $file" >> "$OUTPUT_FILE"
        cat "$file" >> "$OUTPUT_FILE"
    else
        echo "Warning: File '$file' not found, skipping." >> "$OUTPUT_FILE"
    fi
done < "$FILE_LIST"

echo "Context file generated: $OUTPUT_FILE"
