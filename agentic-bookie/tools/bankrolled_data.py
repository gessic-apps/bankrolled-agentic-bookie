import firebase_admin
from firebase_admin import credentials, firestore
import json
import heapq
def fetch_recent_predictions_collection_group(limit=200):
    """
    Fetches the most recent predictions using a collection group query.
    
    Args:
        limit (int): Maximum number of documents to retrieve
    
    Returns:
        list: List of dictionaries representing the documents, sorted by date
    """
    # Initialize Firestore client
    if not firebase_admin._apps:
        cred = credentials.Certificate('/Users/osman/bankrolled-agent-bookie/agentic-bookie/bankrolledtg-firebase-adminsdk-1rt0t-5980d07f2b.json')
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    
    # Collection group query for all 'items' subcollections
    # This will get all 'items' collections regardless of their path
    items_ref = db.collection_group('predictions')
    
    # Query documents and order by date field
    # Replace 'timestamp' with your actual date field name
    query = items_ref.order_by('eventReadableDate', direction=firestore.Query.DESCENDING).limit(limit)
    
    docs = query.stream()
    
    # Convert documents to dictionaries and include path information
    result = []
    for doc in docs:
        doc_dict = doc.to_dict()
        doc_dict['id'] = doc.id
        
        # Get the full path to include user information
        path_parts = doc.reference.path.split('/')
        if len(path_parts) >= 4:  # users/user_id/predictions/prediction_id/items/item_id
            doc_dict['user_id'] = path_parts[1]
            doc_dict['prediction_id'] = path_parts[3]
        
        result.append(doc_dict)
    
    return result

# Usage
if __name__ == "__main__":
    # Fetch data using collection group query
    data = fetch_recent_predictions_collection_group()
    
    # Print summary
    print(f"Retrieved {len(data)} documents")
    
    # Save to file
    with open('recent_predictions.json', 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    # Example of accessing the data
    if data:
        print("\nExample document:")
        print(json.dumps(data[0], indent=2, default=str))