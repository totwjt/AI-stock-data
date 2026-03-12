# 启动脚本使用说明

## 功能概述

`start.sh` 是 Ai-TuShare 项目的一键启动脚本，支持启动多个可选模块：

- **app**: 股票API服务（端口 8000）
- **web**: 数据同步Web查询界面（端口 8001）

## 使用方法

### 1. 查看帮助
```bash
./start.sh --help
```

### 2. 启动单个模块
```bash
# 后台启动股票API服务
./start.sh app

# 前台启动股票API服务（支持Ctrl+C中断）
./start.sh -f app

# 后台启动Web查询界面
./start.sh web

# 前台启动Web查询界面（支持Ctrl+C中断）
./start.sh -f web
```

### 3. 启动所有模块
```bash
./start.sh all
```

### 4. 停止模块
```bash
# 停止股票API服务
./start.sh --stop app

# 停止Web查询界面
./start.sh --stop web

# 停止所有模块
./start.sh --stop
```

### 5. 查看运行状态
```bash
./start.sh --list
```

## 模块说明

### 股票API服务 (app)
- **功能**: 提供实时股票数据API接口和Web看板
- **端口**: 8000
- **访问地址**: http://localhost:8000
- **数据源**: Tushare Pro (实时API调用)
- **数据库**: SQLite (API日志和缓存)

### 数据同步Web查询 (web)
- **功能**: 提供PostgreSQL数据库的Web查询界面
- **端口**: 8001
- **访问地址**: http://localhost:8001
- **数据源**: PostgreSQL (历史数据)
- **功能**: 浏览表结构、查看表数据

## 日志文件

- 主API服务日志: `/tmp/ai_tushare_logs/app.log`
- Web查询界面日志: `/tmp/ai_tushare_logs/web.log`

## 进程PID文件

- 主API服务PID: `/tmp/ai_tushare_pids/app.pid`
- Web查询界面PID: `/tmp/ai_tushare_pids/web.pid`

## 注意事项

1. **端口冲突**: 如果端口被占用，脚本会提示并询问是否清理
2. **虚拟环境**: 脚本会自动检查并创建虚拟环境
3. **依赖安装**: 脚本会自动安装缺少的依赖
4. **Ctrl+C中断**: 启动模块后，按 Ctrl+C 可停止当前模块
5. **多模块启动**: 同时启动多个模块时，每个模块独立运行