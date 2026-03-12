#!/bin/bash

# Ai-TuShare 启动脚本
# 功能：检查端口占用、清理进程、启动应用

set -e  # 遇到错误立即退出

# 配置
PORT=8000
APP_MODULE="app.main"
VENV_PATH="./venv/bin/python"
LOG_FILE="/tmp/app.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Ai-TuShare 启动脚本 ===${NC}"
echo ""

# 1. 检查端口占用情况
echo -e "${YELLOW}步骤 1: 检查端口 $PORT 占用情况...${NC}"
if lsof -i :$PORT > /dev/null 2>&1; then
    echo -e "${RED}端口 $PORT 已被占用${NC}"
    echo "占用进程："
    lsof -i :$PORT
    
    # 询问是否清理
    read -p "是否清理占用端口的进程？(y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}正在清理端口 $PORT 的进程...${NC}"
        # 获取进程ID并杀掉
        PIDS=$(lsof -t -i:$PORT)
        if [ ! -z "$PIDS" ]; then
            kill -9 $PIDS 2>/dev/null || true
            sleep 1
            echo -e "${GREEN}已清理进程: $PIDS${NC}"
        fi
    else
        echo -e "${RED}取消启动${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}端口 $PORT 可用${NC}"
fi
echo ""

# 2. 检查Python虚拟环境
echo -e "${YELLOW}步骤 2: 检查Python虚拟环境...${NC}"
if [ ! -f "$VENV_PATH" ]; then
    echo -e "${RED}虚拟环境未找到，正在创建...${NC}"
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
else
    echo -e "${GREEN}虚拟环境已存在${NC}"
fi
echo ""

# 3. 检查依赖包
echo -e "${YELLOW}步骤 3: 检查依赖包...${NC}"
./venv/bin/pip freeze | grep -q "fastapi" || {
    echo -e "${RED}依赖包未安装，正在安装...${NC}"
    ./venv/bin/pip install -r requirements.txt
}
echo -e "${GREEN}依赖包检查完成${NC}"
echo ""

# 4. 检查数据库目录
echo -e "${YELLOW}步骤 4: 检查数据目录...${NC}"
if [ ! -d "data" ]; then
    echo -e "${YELLOW}创建数据目录...${NC}"
    mkdir -p data
fi
echo -e "${GREEN}数据目录检查完成${NC}"
echo ""

# 5. 启动应用
echo -e "${YELLOW}步骤 5: 启动应用...${NC}"
echo "应用日志: $LOG_FILE"
echo "访问地址: http://localhost:$PORT"
echo "API测试页面: http://localhost:$PORT/api-tester"
echo "按 Ctrl+C 停止应用"
echo ""

# 清理旧日志
> "$LOG_FILE"

# 启动应用
"$VENV_PATH" -m "$APP_MODULE" > "$LOG_FILE" 2>&1 &

# 保存进程PID
APP_PID=$!
echo "应用进程PID: $APP_PID"

# 等待应用启动
sleep 3

# 检查应用是否成功启动
if ps aux | grep -v grep | grep -q "$APP_MODULE"; then
    echo -e "${GREEN}✓ 应用启动成功！${NC}"
    echo ""
    echo "日志输出："
    tail -n 10 "$LOG_FILE"
    echo ""
    echo -e "${GREEN}=== 启动完成 ===${NC}"
    echo "访问 http://localhost:$PORT 查看应用"
    echo ""
    
    # 等待用户中断
    echo "应用正在运行...按 Ctrl+C 停止"
    trap "echo -e '\n${YELLOW}正在停止应用...${NC}'; kill $APP_PID 2>/dev/null; echo -e '${GREEN}应用已停止${NC}'; exit 0" INT TERM
    
    # 等待进程结束
    wait $APP_PID
else
    echo -e "${RED}✗ 应用启动失败！${NC}"
    echo "错误日志："
    tail -n 20 "$LOG_FILE"
    exit 1
fi