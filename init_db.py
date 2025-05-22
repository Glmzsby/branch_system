from app import app, db, User
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        # 创建所有数据库表
        db.create_all()
        
        # 定义初始用户数据
        initial_users = [
            
            {
                'username': 'user1',
                'password': '123456',
                'name': '用户1',
                'type': 'normal',
                'role': '普通用户',
                'points': 80
            },
        ]
        
        # 确保所有普通用户的基础分为80
        for user_data in initial_users:
            if user_data['type'] == 'normal':
                user_data['points'] = 80
        
        # 添加用户到数据库
        for user_data in initial_users:
            # 检查用户是否已存在
            if not User.query.filter_by(username=user_data['username']).first():
                user = User(
                    username=user_data['username'],
                    password=generate_password_hash(user_data['password']),
                    name=user_data['name'],
                    type=user_data['type'],
                    role=user_data['role'],
                    points=user_data['points']
                )
                db.session.add(user)
        
        # 提交所有更改
        db.session.commit()

if __name__ == '__main__':
    init_db()
    print('数据库初始化完成！')