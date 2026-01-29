"""
Dashboard API routes for AI Knowledge Base.
Provides REST endpoints for the dashboard frontend.
"""

from flask import Blueprint, jsonify, request

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analytics import (
    get_overall_stats,
    get_category_stats,
    get_trending_topics,
    get_topic_timeline,
    get_whats_hot,
    get_recent_emails,
    get_top_domains
)
from services.tools import (
    get_tool_rankings,
    get_tool_comparison,
    get_tools_by_category,
    get_tool_details
)
from services.briefings import (
    generate_briefing_content,
    generate_ai_briefing,
    format_briefing_html
)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api')


@dashboard_bp.route('/stats')
def api_stats():
    """Get overall knowledge base statistics."""
    stats = get_overall_stats()
    return jsonify(stats)


@dashboard_bp.route('/categories')
def api_categories():
    """Get all categories with counts."""
    categories = get_category_stats()
    return jsonify(categories)


@dashboard_bp.route('/trending')
def api_trending():
    """Get trending topics."""
    days = request.args.get('days', 7, type=int)
    limit = request.args.get('limit', 10, type=int)
    trending = get_trending_topics(days=days, limit=limit)
    return jsonify(trending)


@dashboard_bp.route('/timeline')
def api_timeline():
    """Get topic timeline data for charts."""
    days = request.args.get('days', 30, type=int)
    timeline = get_topic_timeline(days=days)
    return jsonify(timeline)


@dashboard_bp.route('/hot')
def api_hot():
    """Get what's hot right now."""
    limit = request.args.get('limit', 10, type=int)
    hot = get_whats_hot(limit=limit)
    return jsonify(hot)


@dashboard_bp.route('/recent')
def api_recent():
    """Get recent emails."""
    limit = request.args.get('limit', 10, type=int)
    recent = get_recent_emails(limit=limit)
    return jsonify(recent)


@dashboard_bp.route('/domains')
def api_domains():
    """Get top domains."""
    limit = request.args.get('limit', 15, type=int)
    domains = get_top_domains(limit=limit)
    return jsonify(domains)


@dashboard_bp.route('/tools')
def api_tools():
    """Get tool rankings."""
    limit = request.args.get('limit', 20, type=int)
    tools = get_tool_rankings(limit=limit)
    return jsonify(tools)


@dashboard_bp.route('/tools/comparison')
def api_tools_comparison():
    """Get tool comparison matrix."""
    tools = get_tool_comparison()
    return jsonify(tools)


@dashboard_bp.route('/tools/categories')
def api_tools_by_category():
    """Get tools grouped by category."""
    tools = get_tools_by_category()
    return jsonify(tools)


@dashboard_bp.route('/tools/<tool_name>')
def api_tool_details(tool_name):
    """Get details for a specific tool."""
    tool = get_tool_details(tool_name)
    if tool:
        return jsonify(tool)
    return jsonify({'error': 'Tool not found'}), 404


@dashboard_bp.route('/briefing')
def api_briefing():
    """Generate on-demand briefing."""
    use_ai = request.args.get('ai', 'false').lower() == 'true'
    
    if use_ai:
        briefing = generate_ai_briefing()
    else:
        briefing = generate_briefing_content()
        briefing['ai_enhanced'] = False
        briefing['summary'] = None
    
    return jsonify(briefing)


@dashboard_bp.route('/briefing/html')
def api_briefing_html():
    """Generate briefing as formatted HTML."""
    use_ai = request.args.get('ai', 'false').lower() == 'true'
    
    if use_ai:
        briefing = generate_ai_briefing()
    else:
        from services.briefings import _generate_summary_without_ai
        briefing = generate_briefing_content()
        briefing['ai_enhanced'] = False
        briefing['summary'] = _generate_summary_without_ai(briefing)
    
    html = format_briefing_html(briefing)
    return html, 200, {'Content-Type': 'text/html'}
