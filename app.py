from flask import Flask, render_template, request, redirect, url_for, abort
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# データベースファイルパス
DATABASE = 'database.db'

# 管理者認証情報 (簡易的なものなので、本番環境ではよりセキュアな方法を検討)
# 環境変数から取得。設定されていない場合はデフォルト値を使用
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'password')

# カテゴリリスト
CATEGORIES = ['なんでも放談', 'その他']

def get_db():
    """データベース接続を取得"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # 辞書形式で結果を取得
    return conn

def init_db():
    """データベースの初期化 (テーブル作成)"""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                radio_name TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        db.commit()
        db.close()

# アプリケーション起動時にデータベースを初期化
init_db()

# 管理者認証デコレーター (DRY原則のため関数化)
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == ADMIN_USERNAME and auth.password == ADMIN_PASSWORD):
            return ('管理者ログインが必要です', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('submit_form'))

@app.route('/submit', methods=['GET', 'POST'])
def submit_form():
    """お便り投稿フォーム"""
    if request.method == 'POST':
        radio_name = request.form['radio_name']
        content = request.form['content']
        category = request.form['category']

        if not radio_name or not content or not category:
            return render_template('submit.html', categories=CATEGORIES, error='ラジオネーム、内容、カテゴリは必須です。')

        if category not in CATEGORIES:
            return render_template('submit.html', categories=CATEGORIES, error='不正なカテゴリが選択されました。')

        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO submissions (radio_name, content, category, created_at) VALUES (?, ?, ?, ?)',
                       (radio_name, content, category, datetime.now().isoformat()))
        db.commit()
        db.close()
        return render_template('submit.html', categories=CATEGORIES, success='お便りありがとうございます！')
    return render_template('submit.html', categories=CATEGORIES)

@app.route('/admin')
@admin_required
def admin_dashboard():
    """管理者ページ - お便り一覧"""
    selected_category = request.args.get('category')
    
    db = get_db()
    cursor = db.cursor()
    
    if selected_category and selected_category != '全て':
        submissions = cursor.execute('SELECT * FROM submissions WHERE category = ? ORDER BY created_at DESC', (selected_category,)).fetchall()
    else:
        submissions = cursor.execute('SELECT * FROM submissions ORDER BY created_at DESC').fetchall()
    
    db.close()
    return render_template('admin.html', submissions=submissions, categories=CATEGORIES, selected_category=selected_category)

@app.route('/admin/submission/<int:submission_id>')
@admin_required
def submission_detail(submission_id):
    """管理者ページ - お便り個別表示"""
    db = get_db()
    cursor = db.cursor()
    
    submission = cursor.execute('SELECT * FROM submissions WHERE id = ?', (submission_id,)).fetchone()
    
    if submission is None:
        abort(404) # お便りが見つからない場合は404エラー
        
    # 前後の投稿IDを取得 (オプション機能)
    prev_submission_id = cursor.execute('SELECT id FROM submissions WHERE id < ? ORDER BY id DESC LIMIT 1', (submission_id,)).fetchone()
    next_submission_id = cursor.execute('SELECT id FROM submissions WHERE id > ? ORDER BY id ASC LIMIT 1', (submission_id,)).fetchone()

    db.close()

    prev_id = prev_submission_id[0] if prev_submission_id else None
    next_id = next_submission_id[0] if next_submission_id else None
    
    return render_template('submission_detail.html', 
                           submission=submission,
                           prev_id=prev_id,
                           next_id=next_id)

@app.route('/admin/submission/delete/<int:submission_id>', methods=['POST'])
@admin_required
def delete_submission(submission_id):
    """管理者ページ - お便り削除"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('DELETE FROM submissions WHERE id = ?', (submission_id,))
    db.commit()
    db.close()
    
    return redirect(url_for('admin_dashboard')) # 削除後、一覧ページに戻る

if __name__ == '__main__':
    app.run(debug=True)