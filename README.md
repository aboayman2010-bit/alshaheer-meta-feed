# هايبر الشهير — مزامنة «وفر أكثر» مع ميتا

هذا المستودع ينشئ تغذية **Supplementary Feed** تضيف تصنيف `custom_label_0` لمنتجات قسم «وفر أكثر» في Easy Orders، ولا تعدّل الأسعار أو الصور في كتالوج ميتا الأساسي.

## إعداد لمرة واحدة

1. **Settings → Secrets and variables → Actions → New repository secret**: الاسم `EASYORDERS_API_KEY` والقيمة **مفتاح Easy Orders جديد بصلاحية قراءة المنتجات فقط**. لا تضع المفتاح في ملفات المستودع.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. **Actions → Publish Savings to Meta → Run workflow**.
4. بعد نجاح مهمتي build وdeploy افتح:
   https://aboayman2010-bit.github.io/alshaheer-meta-feed/supplementary_savings.csv
5. داخل Commerce Manager أضف الرابط باعتباره **Supplementary feed** للكتالوج الحالي (لا تنشئ كتالوجًا جديدًا)، واضبط تحديثًا مجدولًا.
6. أنشئ Product Set بفلتر `custom_label_0 = وفر اكثر`.

سيُحدّث GitHub Actions الملف كل ساعة تقريبًا، وقد يتأخر التنفيذ وسحب ميتا. المنتجات التي تخرج من القسم تصبح `other`. المنتجات غير المؤكدة تُستبعد مؤقتًا (كما اتفقنا)، والفشل غير المعتاد يمنع نشر فيد جديد.

**مهم:** الإصدار الحالي ينشئ صفوف تصنيف لكل المنتجات التي يرجعها Easy Orders؛ ميتا يجب أن تطابقها حسب `id` مع كتالوجها الأساسي، وقد تتجاهل معرفات غير موجودة. لا ترفع CSV باعتباره مصدرًا أساسيًا.

يجب التأكد أن `custom_label_0` غير مستخدم بالفعل لغرض آخر. ملفات التصنيف المنشورة عامة، لكنها لا تحتوي على مفتاح API. استبدل المفتاح الذي ظهر في المحادثة بمفتاح جديد للقراءة فقط.