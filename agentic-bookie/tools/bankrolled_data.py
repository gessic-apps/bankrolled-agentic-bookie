import firebase_admin
from firebase_admin import credentials, firestore
import json
import heapq
import os
from datetime import datetime, timedelta, timezone # Import datetime components

# Rename function to reflect the new filter
def fetch_predictions_last_two_days():
    """
    Fetches predictions from the last two days using a collection group query.

    Returns:
        list: List of dictionaries representing the documents, sorted by date
    """
    # Initialize Firestore client
    if not firebase_admin._apps:
        cred = credentials.Certificate('/home/osman/bankrolled-agent-bookie/agentic-bookie/bankrolledtg-firebase-adminsdk-1rt0t-5980d07f2b.json')
        # cred = credentials.Certificate('/Users/osman/bankrolled-agent-bookie/agentic-bookie/bankrolledtg-firebase-adminsdk-1rt0t-5980d07f2b.json')
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    # Calculate the timestamp for two days ago (using UTC for consistency)
    two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)

    # Collection group query for all 'predictions' subcollections
    items_ref = db.collection_group('predictions')

    # Query documents: filter by date >= two_days_ago, then order
    # Assumes 'eventReadableDate' is a Timestamp or comparable string format
    query = items_ref.where('eventReadableDate', '>=', two_days_ago)\
                     .order_by('eventReadableDate', direction=firestore.Query.DESCENDING)

    docs = query.stream()

    # Convert documents to dictionaries and include path information
    result = []
    for doc in docs:
        doc_dict = doc.to_dict()
        doc_dict['id'] = doc.id

        # Get the full path to include user information
        path_parts = doc.reference.path.split('/')
        # Ensure the path structure is as expected
        if len(path_parts) >= 4 and path_parts[0] == 'users' and path_parts[2] == 'predictions':
             doc_dict['user_id'] = path_parts[1]
             # The prediction ID is actually the document ID itself in a collection group query
             # If 'predictions' is the collection group, the path is users/{uid}/predictions/{pid}
             # If 'items' were the group, path: users/{uid}/predictions/{pid}/items/{itemid}
             # Assuming 'predictions' is the collection group as per the query
             doc_dict['prediction_id'] = doc.id # The ID of the document in the predictions collection
        elif len(path_parts) >= 6 and path_parts[0] == 'users' and path_parts[2] == 'predictions' and path_parts[4] == 'items':
             # Handle the older path structure if 'items' was the collection group before
             doc_dict['user_id'] = path_parts[1]
             doc_dict['prediction_id'] = path_parts[3] # ID of the parent prediction doc
             doc_dict['item_id'] = doc.id # ID of the item doc

        result.append(doc_dict)

    return result

# Usage
if __name__ == "__main__":
    # Fetch data using the updated function
    data = fetch_predictions_last_two_days() # Call the renamed function

    # Print summary
    print(f"Retrieved {len(data)} documents from the last 2 days")

    # Determine the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the full path for the output file - update filename
    output_file_path = os.path.join(script_dir, 'predictions_last_two_days.json')

    # Save to file in the script's directory
    with open(output_file_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Data saved to {output_file_path}")

    # Example of accessing the data (optional)
    # if data:
    #     print("\nExample document:")
    #     print(json.dumps(data[0], indent=2, default=str))