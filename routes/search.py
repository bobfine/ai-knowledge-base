"""
Search API routes for AI Knowledge Base.
Provides REST endpoints for semantic search and entity browsing.
"""

from flask import Blueprint, jsonify, request

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.search import hybrid_search, synthesize_answer, get_related_searches, search_with_filters
from services.embeddings import get_embedding_stats
from services.entities import get_entity_list, get_entity_details

search_bp = Blueprint('search', __name__, url_prefix='/api')


@search_bp.route('/search')
def api_search():
    """
    Search the knowledge base.
    
    Query params:
    - q: search query (required)
    - limit: max results (default 10)
    - synthesize: include AI synthesis (default false)
    - category: filter by category
    - entity: filter by entity name
    """
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    limit = request.args.get('limit', 10, type=int)
    synthesize = request.args.get('synthesize', 'false').lower() == 'true'
    
    # Build filters
    filters = {}
    if request.args.get('category'):
        filters['category'] = request.args.get('category')
    if request.args.get('entity'):
        filters['entity'] = request.args.get('entity')
    if request.args.get('date_from'):
        filters['date_from'] = request.args.get('date_from')
    if request.args.get('date_to'):
        filters['date_to'] = request.args.get('date_to')
    
    # Perform search
    if filters:
        results = search_with_filters(query, filters, limit=limit)
    else:
        results = hybrid_search(query, limit=limit)
    
    response = {
        'query': query,
        'results': results,
        'total': len(results)
    }
    
    # Add AI synthesis if requested
    if synthesize:
        synthesis = synthesize_answer(query, results)
        response['synthesis'] = synthesis
    
    # Add related searches
    related = get_related_searches(query, limit=5)
    if related:
        response['related_searches'] = related
    
    return jsonify(response)


@search_bp.route('/search/suggest')
def api_search_suggest():
    """Get search suggestions based on partial query."""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    # Get entities matching query
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, type, mention_count
            FROM entities
            WHERE name LIKE ?
            ORDER BY mention_count DESC
            LIMIT 5
        ''', (f'%{query}%',))
        
        suggestions = [
            {
                'text': row['name'],
                'type': row['type'],
                'count': row['mention_count']
            }
            for row in cursor.fetchall()
        ]
    
    return jsonify(suggestions)


@search_bp.route('/entities')
def api_entities():
    """
    Get list of entities.
    
    Query params:
    - type: filter by entity type (tool, company, concept, person)
    - limit: max results (default 50)
    """
    entity_type = request.args.get('type')
    limit = request.args.get('limit', 50, type=int)
    
    entities = get_entity_list(entity_type=entity_type, limit=limit)
    return jsonify(entities)


@search_bp.route('/entities/<entity_name>')
def api_entity_details(entity_name):
    """Get detailed information about a specific entity."""
    entity = get_entity_details(entity_name)
    if entity:
        return jsonify(entity)
    return jsonify({'error': 'Entity not found'}), 404


@search_bp.route('/embeddings/stats')
def api_embedding_stats():
    """Get statistics about embeddings."""
    stats = get_embedding_stats()
    return jsonify(stats)


# Import get_connection for search suggestions
from database import get_connection
