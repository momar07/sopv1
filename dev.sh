#!/bin/bash

###############################################
# SOB POS Project Automation Script
# التاريخ: 2026-03-04
# الغرض: تطوير وتحسين مشروع POS
###############################################

set -e  # توقف عند أي خطأ

# الألوان للطباعة
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# المسارات
PROJECT_ROOT=$(pwd)
BACKEND_PATH="$PROJECT_ROOT/pos_backend"
FRONTEND_PATH="$PROJECT_ROOT/pos_frontend"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="$PROJECT_ROOT/backups_$TIMESTAMP"

###############################################
# الدوال المساعدة
###############################################

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $1"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# إنشاء نسخة احتياطية
backup_project() {
    print_header "إنشاء نسخة احتياطية"
    mkdir -p "$BACKUP_DIR"
    
    if [ -d "$BACKEND_PATH" ]; then
        cp -r "$BACKEND_PATH" "$BACKUP_DIR/"
        print_success "تم عمل backup للـ Backend"
    fi
    
    if [ -d "$FRONTEND_PATH" ]; then
        cp -r "$FRONTEND_PATH" "$BACKUP_DIR/"
        print_success "تم عمل backup للـ Frontend"
    fi
    
    echo "المسار: $BACKUP_DIR"
}

# إعداد البيئة
setup_environment() {
    print_header "إعداد البيئة"
    
    # Backend
    if [ -d "$BACKEND_PATH" ]; then
        cd "$BACKEND_PATH"
        
        # إنشاء virtual environment إذا لم يكن موجود
        if [ ! -d "venv" ]; then
            print_warning "إنشاء Python virtual environment..."
            python3 -m venv venv
        fi
        
        # تفعيل البيئة
        source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null
        
        # تثبيت المكتبات
        print_warning "تثبيت Django dependencies..."
        pip install -r requirements.txt --upgrade
        
        # تشغيل migrations
        print_warning "تشغيل Database migrations..."
        python manage.py migrate
        
        print_success "Backend جاهز"
        cd "$PROJECT_ROOT"
    fi
    
    # Frontend
    if [ -d "$FRONTEND_PATH" ]; then
        cd "$FRONTEND_PATH"
        
        # تثبيت npm dependencies
        if [ ! -d "node_modules" ]; then
            print_warning "تثبيت npm dependencies..."
            npm install
        else
            print_warning "تحديث npm dependencies..."
            npm install
        fi
        
        print_success "Frontend جاهز"
        cd "$PROJECT_ROOT"
    fi
}

# تشغيل المشروع في development
run_development() {
    print_header "تشغيل Development Mode"
    
    # تشغيل Backend في background
    if [ -d "$BACKEND_PATH" ]; then
        print_warning "تشغيل Django Backend..."
        cd "$BACKEND_PATH"
        source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null
        python manage.py runserver &
        BACKEND_PID=$!
        print_success "Backend قيد التشغيل (PID: $BACKEND_PID)"
        cd "$PROJECT_ROOT"
    fi
    
    # تشغيل Frontend في الطرف الأمامي
    if [ -d "$FRONTEND_PATH" ]; then
        print_warning "تشغيل React Frontend..."
        cd "$FRONTEND_PATH"
        npm run dev
    fi
}

# تنظيف الملفات غير الضرورية
clean_project() {
    print_header "تنظيف المشروع"
    
    # Backend
    find "$BACKEND_PATH" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$BACKEND_PATH" -type f -name "*.pyc" -delete 2>/dev/null || true
    rm -rf "$BACKEND_PATH/.pytest_cache" 2>/dev/null || true
    print_success "تم تنظيف Backend"
    
    # Frontend
    rm -rf "$FRONTEND_PATH/dist" 2>/dev/null || true
    rm -rf "$FRONTEND_PATH/.vite" 2>/dev/null || true
    print_success "تم تنظيف Frontend"
}

# بناء المشروع للإنتاج
build_production() {
    print_header "بناء Production Build"
    
    if [ -d "$FRONTEND_PATH" ]; then
        cd "$FRONTEND_PATH"
        print_warning "بناء Frontend..."
        npm run build
        print_success "تم بناء Frontend بنجاح"
        cd "$PROJECT_ROOT"
    fi
}

# تشغيل الاختبارات
run_tests() {
    print_header "تشغيل الاختبارات"
    
    if [ -d "$BACKEND_PATH" ]; then
        cd "$BACKEND_PATH"
        source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null
        print_warning "تشغيل Django tests..."
        python manage.py test 2>/dev/null || print_error "لا توجد اختبارات"
        cd "$PROJECT_ROOT"
    fi
}

# عرض الحالة
show_status() {
    print_header "حالة المشروع"
    
    echo -e "${BLUE}Backend:${NC}"
    if [ -d "$BACKEND_PATH" ]; then
        echo "  ✓ موجود: $BACKEND_PATH"
        [ -f "$BACKEND_PATH/requirements.txt" ] && echo "  ✓ requirements.txt موجود"
        [ -f "$BACKEND_PATH/manage.py" ] && echo "  ✓ Django setup موجود"
    else
        echo "  ✗ Backend غير موجود"
    fi
    
    echo -e "${BLUE}Frontend:${NC}"
    if [ -d "$FRONTEND_PATH" ]; then
        echo "  ✓ موجود: $FRONTEND_PATH"
        [ -f "$FRONTEND_PATH/package.json" ] && echo "  ✓ package.json موجود"
        [ -d "$FRONTEND_PATH/node_modules" ] && echo "  ✓ node_modules مثبت" || echo "  ⚠ node_modules غير مثبت"
    else
        echo "  ✗ Frontend غير موجود"
    fi
}

# القائمة الرئيسية
show_menu() {
    echo -e "\n${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  SOB POS - أتمتة المشروع"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}\n"
    
    echo "1) حالة المشروع"
    echo "2) إعداد البيئة"
    echo "3) تنظيف المشروع"
    echo "4) تشغيل Development"
    echo "5) بناء Production"
    echo "6) تشغيل الاختبارات"
    echo "7) عمل Backup"
    echo "8) الخروج"
    echo ""
}

###############################################
# البرنامج الرئيسي
###############################################

if [ $# -eq 0 ]; then
    # الوضع التفاعلي
    while true; do
        show_menu
        read -p "اختر خياراً (1-8): " choice
        
        case $choice in
            1) show_status ;;
            2) setup_environment ;;
            3) clean_project ;;
            4) run_development ;;
            5) build_production ;;
            6) run_tests ;;
            7) backup_project ;;
            8) print_success "وداعاً!"; exit 0 ;;
            *) print_error "خيار غير صحيح" ;;
        esac
    done
else
    # الوضع بسطر الأوامر
    case $1 in
        setup) setup_environment ;;
        clean) clean_project ;;
        dev) run_development ;;
        build) build_production ;;
        test) run_tests ;;
        backup) backup_project ;;
        status) show_status ;;
        *) echo "الخيارات: setup, clean, dev, build, test, backup, status" ;;
    esac
fi


