# 党员管理系统

这是一个基于Flask和Vue.js的党员管理系统，支持普通党员和支部委员两种角色的登录，以及后台管理系统。

## 功能特点

- 支持两种登录模式：普通党员和支部委员
- 支部委员可以审核活动和加分申请
- 积分排行榜（总榜、月榜、周榜）
- 后台管理系统（仅支部书记可访问）
- 用户管理（增删改查）

## 技术栈

- 前端：HTML5, CSS3, JavaScript
- 后端：Python Flask
- 数据库：SQLite（开发环境）/ MySQL（生产环境）
- 认证：JWT (JSON Web Token)

## 安装说明

1. 克隆项目到本地：
```bash
git clone [项目地址]
cd [项目目录]
```

2. 创建并激活虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 初始化数据库：
```bash
python app.py
```

## 测试账号

系统预置了以下测试账号：

1. 普通党员
   - 用户名：test
   - 密码：12345679

2. 组织委员
   - 用户名：test1
   - 密码：12345679

3. 宣传委员
   - 用户名：test2
   - 密码：12345679

4. 支部书记（可访问后台管理系统）
   - 用户名：test3
   - 密码：12345679

## 部署到PythonAnywhere

1. 在PythonAnywhere上创建新的Web应用
2. 选择Flask框架
3. 上传项目文件
4. 配置虚拟环境并安装依赖
5. 配置数据库（使用MySQL）
6. 配置WSGI文件
7. 配置静态文件路径
8. 重启Web应用

## 开发说明

- 前端文件位于 `static` 目录
- 后端API位于 `app.py`
- 数据库模型定义在 `app.py` 中
- 静态文件（CSS、JS）位于 `static` 目录

## 注意事项

1. 确保在生产环境中修改默认的密钥
2. 定期备份数据库
3. 使用HTTPS进行安全传输
4. 定期更新依赖包以修复安全漏洞

## 许可证

MIT License 