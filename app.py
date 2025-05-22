from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta, timezone
from config import current_config

app = Flask(__name__, static_folder='static')
CORS(app)
app.config.from_object(current_config)

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 配置JWT
jwt = JWTManager(app)
jwt.init_app(app)

# 添加JWT错误处理
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'success': False,
        'message': 'Token已过期，请重新登录'
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({
        'success': False,
        'message': '无效的Token，请重新登录'
    }), 401

@jwt.unauthorized_loader
def unauthorized_callback(error):
    return jsonify({
        'success': False,
        'message': '未提供Token，请先登录'
    }), 401

@app.route('/admin/<path:filename>')
def serve_admin(filename):
    return send_from_directory('admin', filename)

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'normal' or 'branch'
    role = db.Column(db.String(20), nullable=False)
    points = db.Column(db.Integer, default=80)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    points = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, ongoing, completed
    applicant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    main_responsible_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = db.Column(db.DateTime)
    
    # 次要负责人关联表
    sub_responsibles = db.relationship('User', secondary='activity_sub_responsibles',
                                     backref=db.backref('sub_activities', lazy='dynamic'))
    
    # 活动参与者关联表
    participants = db.relationship('User', secondary='activity_participants',
                                 backref=db.backref('participated_activities', lazy='dynamic'))

class ActivitySubResponsible(db.Model):
    __tablename__ = 'activity_sub_responsibles'
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class PointsRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = db.Column(db.DateTime)

class ActivityParticipant(db.Model):
    __tablename__ = 'activity_participants'
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# Helper Functions
def is_branch_member(user):
    return user.type == 'branch'

def is_admin(user):
    return user.role == '支部书记'

# API Routes
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    
    if user and check_password_hash(user.password, data['password']):
        if (data['type'] == 'branch' and is_branch_member(user)) or \
           (data['type'] == 'normal' and not is_branch_member(user)):
            access_token = create_access_token(identity=user.id)
            return jsonify({
                'success': True,
                'token': access_token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'name': user.name,
                    'type': user.type,
                    'role': user.role
                }
            })
        return jsonify({'success': False, 'message': '身份类型不匹配'}), 401
        
        access_token = create_access_token(identity=user.id)
        return jsonify({
            'success': True,
            'token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'name': user.name,
                'type': user.type,
                'role': user.role
            }
        })
    
    return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    
    if user and check_password_hash(user.password, data['password']) and is_admin(user):
        access_token = create_access_token(identity=user.id)
        return jsonify({
            'success': True,
            'token': access_token
        })
    
    return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_users():
    current_user = User.query.get(get_jwt_identity())
    if not is_admin(current_user):
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    # 获取所有用户并按积分降序排序
    users = User.query.order_by(User.points.desc()).all()
    
    # 计算每个用户的排名，相同积分获得相同排名
    rankings = {}
    current_rank = 1
    current_points = None
    for i, user in enumerate(users):
        if current_points != user.points:
            current_rank = i + 1
            current_points = user.points
        rankings[user.id] = current_rank
    
    return jsonify({
        'success': True,
        'users': [{
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'type': user.type,
            'role': user.role,
            'points': user.points,
            'rank': rankings[user.id]
        } for user in users]
    })


@app.route('/api/admin/users', methods=['POST'])
@jwt_required()
def create_user():
    current_user = User.query.get(get_jwt_identity())
    if not is_admin(current_user):
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400
    
    # 检查支部委员职务唯一性
    if data['type'] == 'branch' and data['role'] in ['宣传委员', '组织委员', '支部书记']:
        existing_user = User.query.filter_by(type='branch', role=data['role']).first()
        if existing_user:
            return jsonify({'success': False, 'message': f'{data["role"]}职务已存在'}), 400
    
    user = User(
        username=data['username'],
        password=generate_password_hash(data['password']),
        name=data['name'],
        type=data['type'],
        role=data['role']
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/admin/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    current_user = User.query.get(get_jwt_identity())
    if not is_admin(current_user):
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    user = User.query.get_or_404(user_id)
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'type': user.type,
            'role': user.role
        }
    })

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    current_user = User.query.get(get_jwt_identity())
    if not is_admin(current_user):
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if 'username' in data and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'message': '用户名已存在'}), 400
        user.username = data['username']
    
    if 'password' in data:
        user.password = generate_password_hash(data['password'])
    
    if 'name' in data:
        user.name = data['name']
    
    if 'type' in data:
        user.type = data['type']
    
    if 'role' in data:
        # 检查支部委员职务唯一性
        if data.get('type', user.type) == 'branch' and data['role'] in ['宣传委员', '组织委员', '支部书记']:
            existing_user = User.query.filter(User.id != user_id, User.type == 'branch', User.role == data['role']).first()
            if existing_user:
                return jsonify({'success': False, 'message': f'{data["role"]}职务已存在'}), 400
        user.role = data['role']
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/user/info', methods=['GET'])
@jwt_required()
def get_user_info():
    try:
        current_user = User.query.get(get_jwt_identity())
        if not current_user:
            return jsonify({
                'success': False,
                'message': '获取用户信息失败'
            }), 404
        
        # 获取所有用户并按积分降序排序
        users = User.query.order_by(User.points.desc()).all()
        
        # 找到当前用户的排名
        user_rank = next((index + 1 for index, user in enumerate(users) if user.id == current_user.id), None)
        
        return jsonify({
            'success': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'name': current_user.name,
                'type': current_user.type,
                'role': current_user.role,
                'points': current_user.points,
                'rank': user_rank,
                'total_users': len(users)
            }
        })
    except Exception as e:
        print('获取用户信息错误:', str(e))
        return jsonify({
            'success': False,
            'message': f'获取用户信息失败: {str(e)}'
        }), 500

@app.route('/api/user/points', methods=['GET'])
@jwt_required()
def get_user_points():
    try:
        current_user = User.query.get(get_jwt_identity())
        if not current_user:
            return jsonify({
                'success': False,
                'message': '获取用户信息失败'
            }), 404
        
        # 获取所有用户并按积分降序排序
        users = User.query.order_by(User.points.desc()).all()
        
        # 找到当前用户的排名
        user_rank = next((index + 1 for index, user in enumerate(users) if user.id == current_user.id), None)
        
        return jsonify({
            'success': True,
            'points': current_user.points,
            'rank': user_rank,
            'total_users': len(users)
        })
    except Exception as e:
        print('获取积分错误:', str(e))
        return jsonify({
            'success': False,
            'message': f'获取积分失败: {str(e)}'
        }), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    current_user = User.query.get(get_jwt_identity())
    if not is_admin(current_user):
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/points/apply', methods=['POST'])
@jwt_required()
def apply_points():
    current_user = User.query.get(get_jwt_identity())
    
    # 获取表单数据
    category = request.form.get('category')
    subcategory = request.form.get('subcategory')
    summary = request.form.get('summary')
    hours = request.form.get('hours')
    
    # 获取上传的文件
    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': '请上传支撑材料'}), 400
    
    # 计算积分
    points = 0
    if category in contributionCategories and subcategory in contributionCategories[category]:
        points = contributionCategories[category][subcategory]
        if category == '其他贡献' and hours:
            points *= int(hours)
    else:
        return jsonify({'success': False, 'message': '无效的贡献类型'}), 400
    
    # 创建积分记录
    points_record = PointsRecord(
        user_id=current_user.id,
        points=points,
        reason=f'{category}-{subcategory}: {summary}',
        status='pending'
    )
    
    db.session.add(points_record)
    db.session.commit()
    
    return jsonify({'success': True})



@app.route('/api/activity/review/list', methods=['GET'])
@jwt_required()
def get_activity_review_list():
    current_user = User.query.get(get_jwt_identity())
    if not is_branch_member(current_user):
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    # 获取所有待审核的活动，按创建时间倒序排序
    pending_activities = Activity.query.filter_by(status='pending').order_by(Activity.created_at.desc()).all()
    
    activities = [{
        'id': activity.id,
        'title': activity.title,
        'description': activity.description,
        'points': activity.points,
        'start_time': activity.start_time.strftime('%Y-%m-%d %H:%M:%S'),
        'end_time': activity.end_time.strftime('%Y-%m-%d %H:%M:%S'),
        'applicant': User.query.get(activity.applicant_id).name,
        'created_at': activity.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for activity in pending_activities]
    
    return jsonify({
        'success': True,
        'activities': activities
    })

@app.route('/api/points/review/list', methods=['GET'])
@jwt_required()
def get_points_review_list():
    current_user = User.query.get(get_jwt_identity())
    if not is_branch_member(current_user):
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    # 获取所有待审核的积分记录
    pending_records = PointsRecord.query.filter_by(status='pending').all()
    
    applications = []
    for record in pending_records:
        user = User.query.get(record.user_id)
        try:
            applications.append({
                'id': record.id,
                'userName': user.name,
                'category': record.reason.split('-')[0],
                'subcategory': record.reason.split('-')[1].split(':')[0].strip(),
                'summary': record.reason.split(':')[1].strip(),
                'points': record.points
            })
        except Exception as e:
            continue
    
    return jsonify({
        'success': True,
        'applications': applications
    })

@app.route('/api/points/review', methods=['POST'])
@jwt_required()
def review_points():
    current_user = User.query.get(get_jwt_identity())
    if not is_branch_member(current_user):
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    data = request.get_json()
    record_id = data.get('applicationId')
    approved = data.get('approved')
    
    record = PointsRecord.query.get_or_404(record_id)
    if record.status != 'pending':
        return jsonify({'success': False, 'message': '该申请已被审核'}), 400
    
    record.status = 'approved' if approved else 'rejected'
    record.reviewer_id = current_user.id
    record.reviewed_at = datetime.utcnow()
    
    if approved:
        user = User.query.get(record.user_id)
        user.points += record.points
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/activity/apply', methods=['POST'])
@jwt_required()
def apply_activity():
    try:
        current_user = User.query.get(get_jwt_identity())
        data = request.get_json()
        
        # 数据验证
        required_fields = ['title', 'description', 'start_time', 'end_time', 'location', 'mainResponsible', 'subResponsibles']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必要字段：{field}'
                }), 400
        
        # 验证时间格式和逻辑
        try:
            start_time = datetime.strptime(data['start_time'], '%Y-%m-%d %H:%M:%S')
            end_time = datetime.strptime(data['end_time'], '%Y-%m-%d %H:%M:%S')
            if start_time >= end_time:
                return jsonify({
                    'success': False,
                    'message': '结束时间必须晚于开始时间'
                }), 400
            if start_time < datetime.now():
                return jsonify({
                    'success': False,
                    'message': '开始时间不能早于当前时间'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'message': '时间格式错误'
            }), 400
        
        # 验证负责人
        main_responsible = User.query.get(data['mainResponsible'])
        if not main_responsible:
            return jsonify({
                'success': False,
                'message': '主要负责人不存在'
            }), 400
            
        for sub_id in data['subResponsibles']:
            if not User.query.get(sub_id):
                return jsonify({
                    'success': False,
                    'message': f'次要负责人ID {sub_id} 不存在'
                }), 400
        
        # 创建新活动
        activity = Activity(
            title=data['title'],
            description=data['description'],
            points=5,  # 主要负责人积分
            start_time=start_time,
            end_time=end_time,
            location=data['location'],
            applicant_id=current_user.id,
            main_responsible_id=int(data['mainResponsible']),  # 设置主要负责人
            status='pending'
        )
        
        db.session.add(activity)
        db.session.flush()  # 获取活动ID
        
        # 添加次要负责人
        for sub_id in data['subResponsibles']:
            sub_responsible = User.query.get(int(sub_id))
            if sub_responsible:
                activity.sub_responsibles.append(sub_responsible)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '活动申请提交成功'
        })
        
    except Exception as e:
        db.session.rollback()
        print('活动申请错误:', str(e))
        return jsonify({
            'success': False,
            'message': '服务器处理请求时发生错误'
        }), 500

@app.route('/api/activity/list', methods=['GET'])
@jwt_required()
def get_activity_list():
    try:
        current_user = User.query.get(get_jwt_identity())
        if not current_user:
            return jsonify({
                'success': False,
                'message': '用户未找到'
            }), 404

        # 获取所有活动，按创建时间倒序排序
        activities = Activity.query.order_by(Activity.created_at.desc()).all()
        activity_list = []
        
        for activity in activities:
            # 获取主要负责人和次要负责人信息
            main_responsible = User.query.get(activity.main_responsible_id)
            sub_responsibles = [user.name for user in activity.sub_responsibles]
            participants = [user.name for user in activity.participants]
            
            # 检查当前用户是否是参与者
            is_participant = current_user in activity.participants
            
            # 检查当前用户是否是申请人
            is_applicant = activity.applicant_id == current_user.id
            
            # 检查活动是否应该显示
            should_show = (
                is_applicant or  # 用户是申请人
                activity.status in ['approved', 'ongoing'] or  # 活动已审核通过或正在进行
                (activity.status == 'completed' and is_participant)  # 活动已完成且用户是参与者
            )
            
            if should_show:
                activity_list.append({
                    'id': activity.id,
                    'title': activity.title,
                    'description': activity.description,
                    'points': activity.points,
                    'start_time': activity.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': activity.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'location': activity.location,
                    'status': activity.status,
                    'applicant': User.query.get(activity.applicant_id).name,
                    'main_responsible': main_responsible.name if main_responsible else None,
                    'sub_responsibles': sub_responsibles,
                    'participants': participants,
                    'is_participant': is_participant,
                    'is_applicant': is_applicant
                })
        
        return jsonify({
            'success': True,
            'activities': activity_list
        })
    except Exception as e:
        print('获取活动列表错误:', str(e))
        return jsonify({
            'success': False,
            'message': f'获取活动列表失败: {str(e)}'
        }), 500

@app.route('/api/activity/review', methods=['POST'])
@jwt_required()
def review_activity():
    try:
        current_user = User.query.get(get_jwt_identity())
        if not is_branch_member(current_user):
            return jsonify({'success': False, 'message': '权限不足'}), 403
        
        data = request.get_json()
        activity_id = data.get('activityId')
        approved = data.get('approved')
        
        activity = Activity.query.get_or_404(activity_id)
        if activity.status != 'pending':
            return jsonify({'success': False, 'message': '该活动已被审核'}), 400
        
        activity.status = 'approved' if approved else 'rejected'
        activity.reviewer_id = current_user.id
        activity.reviewed_at = datetime.utcnow()
        
        # 如果活动已经开始，更新状态为进行中
        if approved and activity.start_time <= datetime.now():
            activity.status = 'ongoing'
        
        # 如果活动已经结束，更新状态并分配积分
        if approved and activity.end_time <= datetime.now():
            activity.status = 'completed'
            # 主要负责人加5分
            main_responsible = User.query.get(activity.main_responsible_id)
            if main_responsible:
                main_responsible.points += 5
                db.session.add(PointsRecord(
                    user_id=main_responsible.id,
                    points=5,
                    reason=f'活动主要负责人：{activity.title}',
                    status='approved'
                ))
            
            # 次要负责人加3分
            for sub_responsible in activity.sub_responsibles:
                sub_responsible.points += 3
                db.session.add(PointsRecord(
                    user_id=sub_responsible.id,
                    points=3,
                    reason=f'活动次要负责人：{activity.title}',
                    status='approved'
                ))
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '审核完成',
            'status': activity.status
        })
    
    except Exception as e:
        db.session.rollback()
        print('活动审核错误:', str(e))
        return jsonify({
            'success': False,
            'message': '服务器处理请求时发生错误'
        }), 500

@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_users_list():
    # 获取所有用户并按积分降序排序
    users = User.query.order_by(User.points.desc()).all()
    
    # 计算每个用户的排名
    rankings = {}
    current_rank = 1
    current_points = None
    for i, user in enumerate(users):
        if current_points != user.points:
            current_rank = i + 1
            current_points = user.points
        rankings[user.id] = current_rank
    
    return jsonify({
        'success': True,
        'users': [{
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'type': user.type,
            'role': user.role,
            'points': user.points,
            'rank': rankings[user.id]
        } for user in users]
    })

@app.route('/api/points/approved', methods=['GET'])
@jwt_required()
def get_approved_points():
    # 获取所有已审核通过的积分记录
    approved_records = PointsRecord.query.filter_by(status='approved').order_by(PointsRecord.reviewed_at.desc()).all()
    
    points = []
    for record in approved_records:
        user = User.query.get(record.user_id)
        points.append({
            'userName': user.name,
            'reason': record.reason,
            'reviewed_at': record.reviewed_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'points': points
    })

# 贡献分类及对应积分
contributionCategories = {
    '教学科研成果及竞赛': {
        '国家级': 30,
        '省级': 20,
        '市县级': 15,
        '校级': 10,
        '院级': 5
    },
    '学业奖': {
        '国家奖学金': 30,
        '校级奖学金一等奖': 10,
        '校级奖学金二等奖': 8,
        '校级奖学金三等奖': 5,
        '单项奖学金': 3
    },
    '荣誉': {
        '优秀毕业生省级': 20,
        '三好学生省级': 20,
        '优秀学生干部省级': 20,
        '先进班级省级': 20,
        '优秀实践团队省级': 20,
        '优秀毕业生校级': 10,
        '三好学生校级': 10,
        '优秀学生干部校级': 10,
        '先进班级校级': 10,
        '优秀实践团队校级': 10,
        '优秀志愿者校级以上': 10,
        '优秀志愿者校级': 6
    },
    '任职': {
        '校级组织主职': 10,
        '校级组织委员': 8,
        '院级组织主职': 8,
        '院级组织委员': 6,
        '班级组织主职': 6,
        '班级组织委员': 4,
        '兴趣社组织主职': 5,
        '兴趣社组织委员': 3
    },
    '创新': {
        '挑战杯': 10,
        '新型团队': 10,
        '结对帮扶': 10
    },
    '其他贡献': {
        '义务劳动': 1,
        '教学助手': 1,
        '体质提升计划': 1
    }
}

@app.route('/api/rankings', methods=['GET'])
@jwt_required()
def get_rankings():
    period = request.args.get('period', 'total')
    
    if period == 'total':
        # 总榜直接返回用户当前积分
        # 首先确保session中的用户数据是最新的
        db.session.commit()
        users = User.query.order_by(User.points.desc()).all()
        rankings = [{
            'name': user.name,
            'points': user.points,
            'userId': user.id
        } for user in users]
    else:
        # 计算指定时间段内的积分变化
        if period == 'month':
            start_date = datetime.utcnow() - timedelta(days=30)
        elif period == 'week':
            start_date = datetime.utcnow() - timedelta(days=7)
        
        # 获取时间段内所有已审核通过的积分记录
        points_records = db.session.query(
            PointsRecord.user_id,
            db.func.sum(PointsRecord.points).label('period_points')
        ).filter(
            PointsRecord.status == 'approved',
            PointsRecord.created_at >= start_date
        ).group_by(PointsRecord.user_id).all()
        
        # 创建用户积分字典
        points_dict = {record.user_id: record.period_points for record in points_records}
        
        # 获取所有用户并计算排名
        users = User.query.all()
        rankings = [{
            'name': user.name,
            'points': points_dict.get(user.id, 0),  # 如果没有记录则返回0分
            'userId': user.id
        } for user in users]
        
        # 按积分降序排序
        rankings.sort(key=lambda x: x['points'], reverse=True)
    
    return jsonify({
        'success': True,
        'rankings': rankings
    })

@app.route('/api/points/personal', methods=['GET'])
@jwt_required()
def get_personal_points():
    try:
        current_user = User.query.get(get_jwt_identity())
        # 获取用户的所有加分申请记录
        points_records = PointsRecord.query.filter_by(user_id=current_user.id).order_by(PointsRecord.created_at.desc()).all()
        
        applications = []
        for record in points_records:
            try:
                category, subcategory_summary = record.reason.split('-', 1)
                subcategory, summary = subcategory_summary.split(':', 1)
                applications.append({
                    'id': record.id,
                    'category': category,
                    'subcategory': subcategory.strip(),
                    'summary': summary.strip(),
                    'points': record.points,
                    'status': record.status,
                    'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                print(f'Error parsing record {record.id}: {str(e)}')
                continue
        
        return jsonify({
            'success': True,
            'applications': applications
        })
    except Exception as e:
        print('获取个人加分申请列表错误:', str(e))
        return jsonify({
            'success': False,
            'message': '获取加分申请列表失败'
        }), 500

@app.route('/api/activity/join', methods=['POST'])
@jwt_required()
def join_activity():
    try:
        current_user = User.query.get(get_jwt_identity())
        data = request.get_json()
        activity_id = data.get('activityId')
        
        activity = Activity.query.get_or_404(activity_id)
        
        # 检查活动状态
        if activity.status != 'approved':
            return jsonify({
                'success': False,
                'message': '该活动不在报名阶段'
            }), 400
        
        # 检查是否已经报名
        if current_user in activity.participants:
            return jsonify({
                'success': False,
                'message': '您已经报名过该活动'
            }), 400
        
        # 添加参与者
        activity.participants.append(current_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '报名成功'
        })
        
    except Exception as e:
        db.session.rollback()
        print('活动报名错误:', str(e))
        return jsonify({
            'success': False,
            'message': '服务器处理请求时发生错误'
        }), 500

# Initialize database and create test users
def init_db():
    with app.app_context():
        db.create_all()
        
        # 更新所有用户的基础分为80
        users = User.query.all()
        for user in users:
            user.points = 80
        db.session.commit()
        
        # Create test users if they don't exist
        test_users = [
            {'username': 'test', 'password': '12345679', 'name': '测试用户1', 'type': 'normal', 'role': '党员'},
            {'username': 'test1', 'password': '12345679', 'name': '测试用户2', 'type': 'branch', 'role': '组织委员'},
            {'username': 'test2', 'password': '12345679', 'name': '测试用户3', 'type': 'branch', 'role': '宣传委员'},
            {'username': 'test3', 'password': '12345679', 'name': '测试用户4', 'type': 'branch', 'role': '支部书记'}
        ]
        
        for user_data in test_users:
            if not User.query.filter_by(username=user_data['username']).first():
                user = User(
                    username=user_data['username'],
                    password=generate_password_hash(user_data['password']),
                    name=user_data['name'],
                    type=user_data['type'],
                    role=user_data['role']
                )
                db.session.add(user)
        
        db.session.commit()

# 添加主页路由
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/main.html')
def main():
    return send_from_directory('.', 'main.html')

@app.route('/admin/')
def admin_index():
    return send_from_directory('admin', 'index.html')

@app.route('/admin/dashboard.html')
def admin_dashboard():
    return send_from_directory('admin', 'dashboard.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)