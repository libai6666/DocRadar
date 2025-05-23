"""
DocRadar - 搜索路由模块
处理文档搜索相关的路由请求
"""
import logging
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
import copy  # 导入copy模块用于深拷贝

from app.core.auth import login_required
from app.utils.search_engine import SearchEngine
from app.core.config import SEARCH_RESULT_LIMIT

# 创建蓝图
search_bp = Blueprint('search', __name__, url_prefix='/search')

# 初始化搜索引擎
search_engine = SearchEngine()

# 搜索历史管理
def get_search_history():
    """获取当前会话的搜索历史"""
    if 'search_history' not in session:
        session['search_history'] = []
    return session['search_history']

def find_existing_search(query):
    """查找是否已存在相同查询的搜索历史
    
    Args:
        query: 搜索查询
        
    Returns:
        (dict, int) or (None, None): 如果找到匹配的搜索历史，返回该条目和索引，否则返回None, None
    """
    history = get_search_history()
    
    # 查找完全匹配的查询
    for index, item in enumerate(history):
        if item['query'].lower() == query.lower():
            logging.info(f"找到已存在的搜索历史: ID={item['id']}, 查询='{query}', 索引={index}")
            return item, index
    
    return None, None

def add_search_history(query, results):
    """添加搜索记录到历史，不改变现有记录的位置"""
    history = get_search_history()
    
    # 检查是否已存在相同查询的搜索历史
    existing_search, existing_index = find_existing_search(query)
    
    if existing_search:
        # 创建历史的深拷贝以避免直接修改session中的对象
        new_history = copy.deepcopy(history)
        
        # 只更新需要的字段，保持其他字段不变
        updated_item = new_history[existing_index]
        updated_item['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        updated_item['results_count'] = len(results)
        updated_item['results'] = results
        
        # 重新设置整个历史
        session['search_history'] = new_history
        logging.info(f"更新搜索历史: 查询='{query}', 结果数={len(results)}, 历史ID={updated_item['id']}, 位置保持在索引={existing_index}")
        
        # 强制保存session
        session.modified = True
        
        return updated_item['id']
    
    # 如果不存在，创建新记录
    # 生成唯一ID
    history_id = 1
    if history:
        history_id = max(item['id'] for item in history) + 1
    
    # 创建新记录
    new_record = {
        'id': history_id,
        'query': query,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'results_count': len(results),
        'results': results  # 存储实际的搜索结果
    }
    
    # 创建历史的深拷贝并添加新记录
    new_history = copy.deepcopy(history)
    new_history.append(new_record)
    session['search_history'] = new_history
    
    # 强制保存session
    session.modified = True
    
    # 记录详细日志
    logging.info(f"添加搜索历史: 查询='{query}', 结果数={len(results)}, 历史ID={history_id}")
    if results:
        result_ids = [r['id'] for r in results]
        logging.info(f"搜索结果ID: {result_ids}")
    
    return history_id

@search_bp.route('', methods=['GET'])
@login_required
def search():
    """搜索页面"""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    # 如果没有查询参数，显示基本搜索页面
    if not query:
        search_history = get_search_history()
        return render_template('results.html', 
                              query='',
                              results=[],
                              search_history=search_history,
                              history_id=None,
                              has_results=False)
    
    # 检查是否已有相同的搜索
    existing_search, _ = find_existing_search(query)
    if existing_search:
        # 如果有相同的搜索，直接使用已有的结果
        logging.info(f"重用已有搜索结果: '{query}'")
        
        # 更新时间戳但不改变位置
        # 使用修改后的add_search_history函数
        add_search_history(query, existing_search['results'])
        
        # 重新获取搜索历史（可能已被更新）
        search_history = get_search_history()
        
        return render_template('results.html',
                              query=query,
                              results=existing_search['results'],
                              search_history=search_history,
                              history_id=existing_search['id'],
                              has_results=len(existing_search['results']) > 0)
    
    # 执行搜索
    results = search_engine.search(query, limit=SEARCH_RESULT_LIMIT)
    logging.info(f"执行搜索: '{query}' 找到 {len(results)} 个结果")
    
    # 记录搜索历史
    if not results:
        logging.warning(f"搜索 '{query}' 未找到结果")
        # 即使没有结果也记录搜索历史
        history_id = add_search_history(query, [])
        search_history = get_search_history()
        
        return render_template('results.html',
                              query=query,
                              results=[],
                              search_history=search_history,
                              history_id=history_id,
                              has_results=False)
    
    # 检查结果格式是否正确
    for i, result in enumerate(results):
        if not isinstance(result, dict) or 'id' not in result:
            logging.error(f"搜索结果 #{i} 格式错误: {result}")
        else:
            if 'title' not in result or not result['title']:
                logging.warning(f"搜索结果 #{i} 的标题为空: id={result['id']}")
            else:
                logging.info(f"搜索结果 #{i}: id={result['id']}, title={result['title']}")
    
    # 有结果，记录搜索历史
    history_id = add_search_history(query, results)
    search_history = get_search_history()
    
    # 直接将搜索结果传递给模板，而不是通过历史记录间接访问
    return render_template('results.html',
                          query=query,
                          results=results,
                          search_history=search_history,
                          history_id=history_id,
                          has_results=True)

@search_bp.route('/api', methods=['GET'])
@login_required
def api_search():
    """搜索API接口"""
    query = request.args.get('q', '')
    limit = request.args.get('limit', SEARCH_RESULT_LIMIT, type=int)
    
    if not query:
        return jsonify({
            'success': False,
            'message': '请提供搜索关键词'
        })
    
    # 检查是否已有相同的搜索
    existing_search, _ = find_existing_search(query)
    if existing_search:
        # 如果有相同的搜索，直接使用已有的结果
        logging.info(f"API重用已有搜索结果: '{query}'")
        
        # 更新时间戳但不改变位置
        add_search_history(query, existing_search['results'])
        
        # 重新获取搜索历史（可能已被更新）
        search_history = get_search_history()
        
        return jsonify({
            'success': True,
            'query': query,
            'results': existing_search['results'],
            'history_id': existing_search['id'],
            'count': len(existing_search['results']),
            'reused': True
        })
    
    # 执行搜索
    results = search_engine.search(query, limit=limit)
    
    # 记录搜索历史
    history_id = add_search_history(query, results)
    
    return jsonify({
        'success': True,
        'query': query,
        'results': results,
        'history_id': history_id,
        'count': len(results),
        'reused': False
    })

@search_bp.route('/delete/<int:history_id>', methods=['GET'])
@login_required
def delete_history(history_id):
    """删除单条搜索历史"""
    history = get_search_history()
    
    # 创建历史的深拷贝
    new_history = copy.deepcopy([item for item in history if item['id'] != history_id])
    
    # 设置新的历史记录
    session['search_history'] = new_history
    
    # 强制保存session
    session.modified = True
    
    logging.info(f"删除搜索历史: ID={history_id}, 剩余历史记录数量={len(new_history)}")
    
    # 如果是AJAX请求，返回JSON响应
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': '搜索历史已删除',
            'remaining_count': len(new_history)
        })
    
    # 返回到原始页面
    return_url = request.args.get('return_to', request.referrer or '/')
    return redirect(return_url)

@search_bp.route('/clear', methods=['GET'])
@login_required
def clear_history():
    """清空所有搜索历史"""
    session['search_history'] = []
    
    # 如果是AJAX请求，返回JSON响应
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': '搜索历史已清空'
        })
    
    # 如果有查询参数，重定向到搜索页面并保留查询
    query = request.args.get('q')
    if query:
        return redirect(url_for('search.search', q=query))
    
    # 返回到原始页面
    return_url = request.args.get('return_to', request.referrer or '/')
    return redirect(return_url)

@search_bp.route('/history', methods=['GET'])
@login_required
def get_history_ajax():
    """获取搜索历史的AJAX接口"""
    search_history = get_search_history()
    
    # 返回JSON格式的搜索历史
    return jsonify({
        'success': True,
        'history': search_history
    }) 