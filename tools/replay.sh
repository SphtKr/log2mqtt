#!/bin/bash
LAST_TS=0

while read -r line; do
    # Extract the first column as the timestamp
    CURRENT_TS=$(echo "$line" | awk '{print $2}')
    
    # Verify the timestamp is a valid number
    if [[ "$CURRENT_TS" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        if (( $(echo "$LAST_TS > 0" | bc -l) )); then
            # Calculate the time difference (supports floating-point decimals)
            DIFF=$(echo "$CURRENT_TS - $LAST_TS" | bc -l)
            
            # Sleep only if the difference is greater than zero
            if (( $(echo "$DIFF > 0" | bc -l) )); then
                # echo sleeping $DIFF
                sleep "$DIFF"
            fi
        fi
        LAST_TS=$CURRENT_TS
    fi
    echo "$line"
done < "$1"