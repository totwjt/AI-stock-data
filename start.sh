#!/bin/bash

# Ai-TuShare 启动脚本
# 功能：启动可选模块（主API服务、数据同步Web查询界面）

set -e  # 遇到错误立即退出

# 配置
VENV_PATH="./venv/bin/python"
LOG_DIR="/tmp/ai_tushare_logs"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 创建日志目录
mkdir -p "$LOG_DIR"

# 进程PID文件
PID_DIR="/tmp/ai_tushare_pids"
mkdir -p "$PID_DIR"

# 模块配置 (使用普通变量替代关联数组以兼容bash 3.x)
MODULE_NAMES=("app" "web")
MODULE_DESCS=("股票API服务" "数据同步Web查询")
MODULE_PORTS=(8000 8001)
MODULE_LOGS=("$LOG_DIR/app.log" "$LOG_DIR/web.log")
MODULE_COMMANDS=("app.main" "data_sync.web.run")

# 获取模块描述
get_module_desc() {
    local module=$1
    for i in "${!MODULE_NAMES[@]}"; do
        if [ "${MODULE_NAMES[$i]}" = "$module" ]; then
            echo "${MODULE_DESCS[$i]}"
            return
        fi
    done
    echo "未知模块"
}

# 获取模块端口
get_module_port() {
    local module=$1
    for i in "${!MODULE_NAMES[@]}"; do
        if [ "${MODULE_NAMES[$i]}" = "$module" ]; then
            echo "${MODULE_PORTS[$i]}"
            return
        fi
    done
    echo "0"
}

# 获取模块日志
get_module_log() {
    local module=$1
    for i in "${!MODULE_NAMES[@]}"; do
        if [ "${MODULE_NAMES[$i]}" = "$module" ]; then
            echo "${MODULE_LOGS[$i]}"
            return
        fi
    done
    echo ""
}

# 获取模块命令
get_module_command() {
    local module=$1
    for i in "${!MODULE_NAMES[@]}"; do
        if [ "${MODULE_NAMES[$i]}" = "$module" ]; then
            echo "${MODULE_COMMANDS[$i]}"
            return
        fi
    done
    echo ""
}

# 显示帮助信息
show_help() {
    echo -e "${GREEN}=== Ai-TuShare 启动脚本 ===${NC}"
    echo ""
    echo "用法: $0 [选项] [模块...]"
    echo ""
    echo "模块:"
    echo "  app      - 启动股票API服务 (端口: 8000)"
    echo "  web      - 启动数据同步Web查询 (端口: 8001)"
    echo "  all      - 启动所有模块"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -s, --stop     停止指定模块"
    echo "  -l, --list     列出正在运行的模块"
    echo "  -f, --foreground 前台启动（支持Ctrl+C中断）"
    echo ""
    echo "示例:"
    echo "  $0 app              # 后台启动股票API服务"
    echo "  $0 -f app           # 前台启动股票API服务（支持Ctrl+C）"
    echo "  $0 web              # 后台启动Web查询界面"
    echo "  $0 all              # 启动所有模块（后台）"
    echo "  $0 -s app           # 停止股票API服务"
    echo "  $0 -l               # 列出正在运行的模块"
}

# 检查端口占用
check_port() {
    local port=$1
    local module=$2
    if lsof -iTCP:$port -sTCP:LISTEN > /dev/null 2>&1; then
        echo -e "${RED}端口 $port ($module) 已被占用${NC}"
        lsof -iTCP:$port -sTCP:LISTEN
        return 1
    else
        echo -e "${GREEN}端口 $port ($module) 可用${NC}"
        return 0
    fi
}

# 启动模块
start_module() {
    local module=$1
    local port=$(get_module_port $module)
    local log_file=$(get_module_log $module)
    local command=$(get_module_command $module)
    local name=$(get_module_desc $module)
    
    # 检查端口
    if ! check_port $port $name; then
        return 1
    fi
    
    # 检查虚拟环境
    if [ ! -f "$VENV_PATH" ]; then
        echo -e "${YELLOW}虚拟环境未找到，正在创建...${NC}"
        python3 -m venv venv
        ./venv/bin/pip install -r requirements.txt
    fi
    
    # 检查依赖
    ./venv/bin/pip freeze | grep -q "fastapi" || {
        echo -e "${YELLOW}依赖包未安装，正在安装...${NC}"
        ./venv/bin/pip install -r requirements.txt
    }
    
    echo -e "${YELLOW}启动 $name...${NC}"
    echo "日志文件: $log_file"
    echo "访问地址: http://localhost:$port"
    
    # 清理旧日志
    > "$log_file"
    
    # 启动应用（使用nohup确保进程独立）
    nohup "$VENV_PATH" -m "$command" > "$log_file" 2>&1 &
    
    # 保存PID
    echo $! > "$PID_DIR/$module.pid"
    
    # 等待启动
    sleep 2
    
    # 检查是否成功启动
    if ps aux | grep -v grep | grep -q "$command"; then
        echo -e "${GREEN}✓ $name 启动成功！${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ $name 启动失败！${NC}"
        echo "错误日志："
        tail -n 20 "$log_file"
        return 1
    fi
}

# 停止模块
stop_module() {
    local module=$1
    local name=$(get_module_desc $module)
    local pid_file="$PID_DIR/$module.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            echo -e "${YELLOW}停止 $name (PID: $pid)...${NC}"
            kill $pid 2>/dev/null
            sleep 1
            # 强制停止
            kill -9 $pid 2>/dev/null || true
            rm -f "$pid_file"
            echo -e "${GREEN}$name 已停止${NC}"
        else
            echo -e "${YELLOW}$name 未运行${NC}"
            rm -f "$pid_file"
        fi
    else
        echo -e "${YELLOW}$name 未运行 (无PID文件)${NC}"
    fi
}

# 列出运行中的模块
list_modules() {
    echo -e "${GREEN}=== 运行中的模块 ===${NC}"
    local running=0
    
    for module in "${MODULE_NAMES[@]}"; do
        local pid_file="$PID_DIR/$module.pid"
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if kill -0 $pid 2>/dev/null; then
                local port=$(get_module_port $module)
                local name=$(get_module_desc $module)
                echo "✓ $name (PID: $pid, 端口: $port)"
                running=1
            else
                rm -f "$pid_file"
            fi
        fi
    done
    
    if [ $running -eq 0 ]; then
        echo "没有运行中的模块"
    fi
}

# 停止所有模块
stop_all() {
    echo -e "${YELLOW}停止所有模块...${NC}"
    for module in "${MODULE_NAMES[@]}"; do
        stop_module $module
    done
}

# 启动前台模块（支持Ctrl+C）
start_foreground() {
    local module=$1
    local port=$(get_module_port $module)
    local log_file=$(get_module_log $module)
    local command=$(get_module_command $module)
    local name=$(get_module_desc $module)
    
    # 检查端口
    if ! check_port $port $name; then
        return 1
    fi
    
    # 检查虚拟环境
    if [ ! -f "$VENV_PATH" ]; then
        echo -e "${YELLOW}虚拟环境未找到，正在创建...${NC}"
        python3 -m venv venv
        ./venv/bin/pip install -r requirements.txt
    fi
    
    # 检查依赖
    ./venv/bin/pip freeze | grep -q "fastapi" || {
        echo -e "${YELLOW}依赖包未安装，正在安装...${NC}"
        ./venv/bin/pip install -r requirements.txt
    }
    
    echo -e "${YELLOW}启动 $name...${NC}"
    echo "日志文件: $log_file"
    echo "访问地址: http://localhost:$port"
    echo "按 Ctrl+C 停止"
    echo ""
    
    # 清理旧日志
    > "$log_file"
    
    # 设置陷阱，确保退出时清理
    trap "echo -e '\n${YELLOW}正在停止 $name...${NC}'; pkill -f \"$command\" 2>/dev/null; echo -e '${GREEN}$name 已停止${NC}'; exit 0" INT TERM
    
    # 前台运行应用
    "$VENV_PATH" -m "$command"
}

# 主函数
main() {
    local action="start"
    local modules=()
    local foreground=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -s|--stop)
                action="stop"
                shift
                ;;
            -l|--list)
                list_modules
                exit 0
                ;;
            -f|--foreground)
                foreground=true
                shift
                ;;
            all)
                modules=("${MODULE_NAMES[@]}")
                shift
                ;;
            app|web)
                modules+=("$1")
                shift
                ;;
            *)
                echo -e "${RED}未知参数: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 如果没有指定模块，显示帮助
    if [ ${#modules[@]} -eq 0 ] && [ "$action" != "stop" ]; then
        show_help
        exit 0
    fi
    
    # 执行操作
    case $action in
        start)
            echo -e "${GREEN}=== Ai-TuShare 启动脚本 ===${NC}"
            echo ""
            
            if [ "$foreground" = true ] && [ ${#modules[@]} -eq 1 ]; then
                # 前台启动单个模块（支持Ctrl+C）
                start_foreground "${modules[0]}"
            else
                # 后台启动模块
                for module in "${modules[@]}"; do
                    start_module $module
                done
                echo ""
                echo -e "${GREEN}=== 启动完成 ===${NC}"
                list_modules
            fi
            ;;
        stop)
            if [ ${#modules[@]} -eq 0 ]; then
                stop_all
            else
                for module in "${modules[@]}"; do
                    stop_module $module
                done
            fi
            ;;
    esac
}

# 运行主函数
main "$@"