import os
import socket

# 获取当前主机名
hostname = socket.gethostname()

# 判断是否在PythonAnywhere上运行
is_pythonanywhere = 'pythonanywhere' in hostname.lower()

# 基础配置
class Config:
    # 数据库配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = 24 * 60 * 60  # 24小时
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # 文件上传配置
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 开发环境配置
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dev.db'
    BASE_URL = 'http://localhost:5000'
    ADMIN_URL = 'http://localhost:5001'

# 生产环境配置
class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///branch.db')
    BASE_URL = 'https://glmzsby.pythonanywhere.com'
    ADMIN_URL = 'https://glmzsby.pythonanywhere.com/admin'

# 根据环境选择配置
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# 导出当前环境的配置
current_config = config['production' if is_pythonanywhere else 'development'] 