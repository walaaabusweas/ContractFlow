# تشغيل الحاويات في الخلفية
up:
	docker-compose up -d

# بناء الحاويات من جديد (بدون كاش لضمان التحديث)
build:
	docker-compose build --no-cache

# إيقاف الحاويات بالكامل
down:
	docker-compose down

# إعادة التشغيل (إيقاف ثم تشغيل)
restart:
	docker-compose down
	docker-compose up -d

# عرض السجلات (Logs) الخاصة بتطبيق FastAPI فقط لمتابعة الـ Agents
logs:
	docker-compose logs -f app

# تنفيذ سكريبت تهيئة المتجهات (Ingestion)
ingest:
	docker-compose exec app python scripts/ingest_policies.py

# الدخول إلى حاوية التطبيق (للـ Debugging اليدوي)
shell:
	docker-compose exec app bash

# الدخول إلى قاعدة البيانات لرؤية الجداول والمتجهات
db-shell:
	docker-compose exec db psql -U postgres -d contractflow_db

# تنظيف الصور غير المستخدمة والـ Volumes المعلقة
clean:
	docker system prune -f
	docker volume prune -f