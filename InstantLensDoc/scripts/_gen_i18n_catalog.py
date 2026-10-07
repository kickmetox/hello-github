#!/usr/bin/env python3
"""Generate InstantLens Doc 2.6.27 i18n catalog + locale help stubs."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOC = ROOT / "instantlensdoc" / "locales"
HELP = LOC / "help"
LOC.mkdir(parents=True, exist_ok=True)
HELP.mkdir(parents=True, exist_ok=True)

LANGS = ("de", "en", "fr", "ru", "es", "zh", "pt", "ar", "it")

# (key, de, en, fr, ru, es, zh, pt, ar, it)
ROWS: list[tuple[str, ...]] = [
    ("settings", "Einstellungen", "Settings", "Paramètres", "Настройки", "Ajustes", "设置", "Definições", "الإعدادات", "Impostazioni"),
    ("settings_title", "InstantLens Doc — Anwendungseinstellungen", "InstantLens Doc — Application settings", "InstantLens Doc — Paramètres de l'application", "InstantLens Doc — Настройки приложения", "InstantLens Doc — Ajustes de la aplicación", "InstantLens Doc — 应用设置", "InstantLens Doc — Definições da aplicação", "InstantLens Doc — إعدادات التطبيق", "InstantLens Doc — Impostazioni applicazione"),
    ("theme", "Design", "Theme", "Thème", "Тема", "Tema", "主题", "Tema", "المظهر", "Tema"),
    ("theme_light", "Hell", "Light", "Clair", "Светлая", "Claro", "浅色", "Claro", "فاتح", "Chiaro"),
    ("theme_dark", "Dunkel", "Dark", "Sombre", "Тёмная", "Oscuro", "深色", "Escuro", "داكن", "Scuro"),
    ("theme_system", "System folgen", "Follow system", "Suivre le système", "Как в системе", "Seguir sistema", "跟随系统", "Seguir sistema", "اتباع النظام", "Segui sistema"),
    ("ui_lang", "Oberflächensprache", "UI language", "Langue de l'interface", "Язык интерфейса", "Idioma de la interfaz", "界面语言", "Idioma da interface", "لغة الواجهة", "Lingua interfaccia"),
    ("ocr_lang", "OCR-Sprache (Standard)", "OCR language (default)", "Langue OCR (défaut)", "Язык OCR (по умолчанию)", "Idioma OCR (predeterminado)", "OCR 语言（默认）", "Idioma OCR (predefinição)", "لغة OCR (افتراضي)", "Lingua OCR (predefinita)"),
    ("batch_dir", "Batch-Ausgabeordner", "Batch output folder", "Dossier de sortie lot", "Папка пакетного вывода", "Carpeta de salida por lotes", "批处理输出文件夹", "Pasta de saída em lote", "مجلد إخراج الدُفعات", "Cartella output batch"),
    ("open_dir", "Standard-Ordner (Öffnen)", "Default folder (Open)", "Dossier par défaut (Ouvrir)", "Папка по умолчанию (Открыть)", "Carpeta predeterminada (Abrir)", "默认文件夹（打开）", "Pasta predefinida (Abrir)", "المجلد الافتراضي (فتح)", "Cartella predefinita (Apri)"),
    ("export_jpeg_q", "Export JPEG-Qualität", "Export JPEG quality", "Qualité JPEG d'export", "Качество JPEG экспорта", "Calidad JPEG de exportación", "导出 JPEG 质量", "Qualidade JPEG de exportação", "جودة JPEG للتصدير", "Qualità JPEG export"),
    ("export_page", "Export PDF-Seitenformat", "Export PDF page size", "Format de page PDF export", "Формат страницы PDF экспорта", "Tamaño de página PDF export", "导出 PDF 页面尺寸", "Formato página PDF exportação", "حجم صفحة PDF للتصدير", "Formato pagina PDF export"),
    ("default_zoom", "Standard-Zoom % (PDF)", "Default zoom % (PDF)", "Zoom par défaut % (PDF)", "Масштаб по умолчанию % (PDF)", "Zoom predeterminado % (PDF)", "默认缩放 % (PDF)", "Zoom predefinido % (PDF)", "التكبير الافتراضي ٪ (PDF)", "Zoom predefinito % (PDF)"),
    ("default_zoom_mode", "Standard-Zoom-Modus (PDF)", "Default zoom mode (PDF)", "Mode de zoom par défaut (PDF)", "Режим масштаба по умолчанию (PDF)", "Modo de zoom predeterminado (PDF)", "默认缩放模式 (PDF)", "Modo de zoom predefinido (PDF)", "وضع التكبير الافتراضي (PDF)", "Modalità zoom predefinita (PDF)"),
    ("autosave_interval", "Autosave-Intervall", "Autosave interval", "Intervalle d'enregistrement auto", "Интервал автосохранения", "Intervalo de autoguardado", "自动保存间隔", "Intervalo de gravação automática", "فاصل الحفظ التلقائي", "Intervallo salvataggio automatico"),
    ("update_check", "Update-Hinweis beim Start", "Update notice on start", "Avis de mise à jour au démarrage", "Уведомление об обновлении при запуске", "Aviso de actualización al iniciar", "启动时更新提示", "Aviso de atualização ao iniciar", "تنبيه التحديث عند البدء", "Avviso aggiornamento all'avvio"),
    ("pick_dir", "Ordner wählen", "Choose folder", "Choisir un dossier", "Выбрать папку", "Elegir carpeta", "选择文件夹", "Escolher pasta", "اختر مجلدًا", "Scegli cartella"),
    ("meta_title", "PDF-Metadaten", "PDF metadata", "Métadonnées PDF", "Метаданные PDF", "Metadatos PDF", "PDF 元数据", "Metadados PDF", "بيانات PDF الوصفية", "Metadati PDF"),
    ("page_size_title", "Seitengröße / Zuschneiden", "Page size / Crop", "Taille de page / Recadrer", "Размер страницы / Обрезка", "Tamaño de página / Recorte", "页面尺寸 / 裁剪", "Tamanho da página / Recorte", "حجم الصفحة / قص", "Dimensione pagina / Ritaglio"),
    ("redact_bake", "Schwärzung einbrennen", "Bake redactions", "Appliquer les caviardages", "Применить редактирование", "Aplicar redacciones", "固化涂黑", "Aplicar redações", "تطبيق التنقيح", "Applica redazioni"),
    ("redact_none", "Keine Schwärzungs-Annotationen.", "No redaction annotations.", "Aucune annotation de caviardage.", "Нет аннотаций редактирования.", "Sin anotaciones de redacción.", "无涂黑注释。", "Sem anotações de redação.", "لا توجد تعليقات تنقيح.", "Nessuna annotazione di redazione."),
    ("redact_clear", "Schwärzungs-Annotationen löschen", "Clear redaction annotations", "Effacer les annotations de caviardage", "Удалить аннотации редактирования", "Borrar anotaciones de redacción", "清除涂黑注释", "Limpar anotações de redação", "مسح تعليقات التنقيح", "Cancella annotazioni di redazione"),
    ("update_title", "Update-Check", "Update check", "Vérification des mises à jour", "Проверка обновлений", "Comprobación de actualizaciones", "更新检查", "Verificação de atualizações", "فحص التحديثات", "Controllo aggiornamenti"),
    ("help", "Hilfe", "Help", "Aide", "Справка", "Ayuda", "帮助", "Ajuda", "مساعدة", "Aiuto"),
    ("about", "Info", "About", "À propos", "О программе", "Acerca de", "关于", "Sobre", "حول", "Informazioni"),
    ("keyboard", "Tastaturhilfe", "Keyboard shortcuts", "Raccourcis clavier", "Горячие клавиши", "Atajos de teclado", "键盘快捷键", "Atalhos de teclado", "اختصارات لوحة المفاتيح", "Scorciatoie da tastiera"),
    ("planned", "Geplant", "Planned", "Prévu", "Запланировано", "Planificado", "计划中", "Planeado", "مخطط", "Pianificato"),
    ("lang_de", "Deutsch", "German", "Allemand", "Немецкий", "Alemán", "德语", "Alemão", "الألمانية", "Tedesco"),
    ("lang_en", "Englisch", "English", "Anglais", "Английский", "Inglés", "英语", "Inglês", "الإنجليزية", "Inglese"),
    ("lang_fr", "Französisch", "French", "Français", "Французский", "Francés", "法语", "Francês", "الفرنسية", "Francese"),
    ("lang_ru", "Russisch", "Russian", "Russe", "Русский", "Ruso", "俄语", "Russo", "الروسية", "Russo"),
    ("lang_es", "Spanisch", "Spanish", "Espagnol", "Испанский", "Español", "西班牙语", "Espanhol", "الإسبانية", "Spagnolo"),
    ("lang_zh", "Chinesisch", "Chinese", "Chinois", "Китайский", "Chino", "中文", "Chinês", "الصينية", "Cinese"),
    ("lang_pt", "Portugiesisch", "Portuguese", "Portugais", "Португальский", "Portugués", "葡萄牙语", "Português", "البرتغالية", "Portoghese"),
    ("lang_ar", "Arabisch", "Arabic", "Arabe", "Арабский", "Árabe", "阿拉伯语", "Árabe", "العربية", "Arabo"),
    ("lang_it", "Italienisch", "Italian", "Italien", "Итальянский", "Italiano", "意大利语", "Italiano", "الإيطالية", "Italiano"),
    ("apply_media", "Seitengröße setzen", "Set page size", "Définir la taille de page", "Задать размер страницы", "Establecer tamaño de página", "设置页面尺寸", "Definir tamanho da página", "تعيين حجم الصفحة", "Imposta dimensione pagina"),
    ("apply_crop", "Zuschneiden (CropBox)", "Crop (CropBox)", "Recadrer (CropBox)", "Обрезать (CropBox)", "Recortar (CropBox)", "裁剪 (CropBox)", "Recortar (CropBox)", "قص (CropBox)", "Ritaglia (CropBox)"),
    ("field_title", "Titel", "Title", "Titre", "Заголовок", "Título", "标题", "Título", "العنوان", "Titolo"),
    ("field_author", "Autor", "Author", "Auteur", "Автор", "Autor", "作者", "Autor", "المؤلف", "Autore"),
    ("field_subject", "Betreff", "Subject", "Sujet", "Тема", "Asunto", "主题", "Assunto", "الموضوع", "Oggetto"),
    ("field_keywords", "Keywords", "Keywords", "Mots-clés", "Ключевые слова", "Palabras clave", "关键词", "Palavras-chave", "الكلمات المفتاحية", "Parole chiave"),
    ("field_creator", "Ersteller", "Creator", "Créateur", "Создатель", "Creador", "创建者", "Criador", "المنشئ", "Creatore"),
    ("field_producer", "Produzent", "Producer", "Producteur", "Производитель", "Productor", "制作程序", "Produtor", "المنتج", "Produttore"),
    ("meta_save", "Speichern", "Save", "Enregistrer", "Сохранить", "Guardar", "保存", "Guardar", "حفظ", "Salva"),
    ("meta_hint", "Titel, Autor, Betreff und Keywords (DocInfo + XMP) — Speichern schreibt in die PDF-Datei.", "Title, author, subject and keywords (DocInfo + XMP) — Save writes into the PDF.", "Titre, auteur, sujet et mots-clés (DocInfo + XMP) — Enregistrer écrit dans le PDF.", "Заголовок, автор, тема и ключевые слова (DocInfo + XMP) — Сохранить записывает в PDF.", "Título, autor, asunto y palabras clave (DocInfo + XMP) — Guardar escribe en el PDF.", "标题、作者、主题和关键词（DocInfo + XMP）— 保存写入 PDF。", "Título, autor, assunto e palavras-chave (DocInfo + XMP) — Guardar grava no PDF.", "العنوان والمؤلف والموضوع والكلمات المفتاحية (DocInfo + XMP) — الحفظ يكتب في PDF.", "Titolo, autore, oggetto e parole chiave (DocInfo + XMP) — Salva scrive nel PDF."),
    ("meta_reset", "Zurücksetzen", "Reset", "Réinitialiser", "Сбросить", "Restablecer", "重置", "Repor", "إعادة تعيين", "Reimposta"),
    ("meta_reset_tip", "Alle Felder auf die geladenen Originalwerte zurücksetzen", "Reset all fields to the loaded original values", "Réinitialiser tous les champs aux valeurs d'origine", "Сбросить все поля к исходным значениям", "Restablecer todos los campos a los valores originales", "将所有字段重置为加载的原始值", "Repor todos os campos para os valores originais", "إعادة جميع الحقول إلى القيم الأصلية", "Reimposta tutti i campi ai valori originali"),
    ("meta_dirty", "Ungespeicherte Änderungen (*)", "Unsaved changes (*)", "Modifications non enregistrées (*)", "Несохранённые изменения (*)", "Cambios sin guardar (*)", "未保存的更改 (*)", "Alterações não guardadas (*)", "تغييرات غير محفوظة (*)", "Modifiche non salvate (*)"),
    ("meta_delete_empty", "Leere Felder beim Speichern löschen", "Delete empty fields on save", "Supprimer les champs vides à l'enregistrement", "Удалять пустые поля при сохранении", "Eliminar campos vacíos al guardar", "保存时删除空字段", "Eliminar campos vazios ao guardar", "حذف الحقول الفارغة عند الحفظ", "Elimina campi vuoti al salvataggio"),
    ("meta_delete_empty_tip", "An: leere Metadaten-Felder aus DocInfo/XMP entfernen. Aus: leere Strings belassen", "On: remove empty metadata fields from DocInfo/XMP. Off: keep empty strings", "Oui: retirer les champs vides de DocInfo/XMP. Non: garder des chaînes vides", "Вкл.: удалять пустые поля из DocInfo/XMP. Выкл.: оставлять пустые строки", "Sí: quitar campos vacíos de DocInfo/XMP. No: mantener cadenas vacías", "开：从 DocInfo/XMP 移除空字段。关：保留空字符串", "Ligado: remover campos vazios de DocInfo/XMP. Desligado: manter cadeias vazias", "تشغيل: إزالة الحقول الفارغة من DocInfo/XMP. إيقاف: الإبقاء على سلاسل فارغة", "On: rimuovi campi vuoti da DocInfo/XMP. Off: mantieni stringhe vuote"),
    ("meta_backup", "Backup (.ildbak) vor Speichern", "Backup (.ildbak) before save", "Sauvegarde (.ildbak) avant enregistrement", "Резервная копия (.ildbak) перед сохранением", "Copia de seguridad (.ildbak) antes de guardar", "保存前备份 (.ildbak)", "Cópia de segurança (.ildbak) antes de guardar", "نسخة احتياطية (.ildbak) قبل الحفظ", "Backup (.ildbak) prima del salvataggio"),
    ("meta_backup_tip", "Vor dem Schreiben eine rotierende Backup-Kopie anlegen", "Create a rotating backup copy before writing", "Créer une copie de sauvegarde rotative avant l'écriture", "Создать ротирующую резервную копию перед записью", "Crear una copia de seguridad rotativa antes de escribir", "写入前创建轮转备份副本", "Criar uma cópia de segurança rotativa antes de escrever", "إنشاء نسخة احتياطية دوّارة قبل الكتابة", "Crea una copia di backup rotativa prima della scrittura"),
    ("meta_toast_ok", "Metadaten gespeichert", "Metadata saved", "Métadonnées enregistrées", "Метаданные сохранены", "Metadatos guardados", "元数据已保存", "Metadados guardados", "تم حفظ البيانات الوصفية", "Metadati salvati"),
    ("meta_toast_empty", "(keine Felder gesetzt)", "(no fields set)", "(aucun champ défini)", "(поля не заданы)", "(sin campos definidos)", "（未设置字段）", "(sem campos definidos)", "(لم تُعيَّن حقول)", "(nessun campo impostato)"),
    ("expiry_warn_banner", "Hinweis: Lizenz/Trial läuft in {rest} ab{until} — Enter/Klick: Info/Aktivierung · Esc / Dismiss / × bis morgen", "Notice: license/trial expires in {rest}{until} — Enter/Click: About/Activate · Esc / Dismiss / × until tomorrow", "Avis : licence/essai expire dans {rest}{until} — Entrée/Clic : À propos/Activer · Échap / Ignorer / × jusqu'à demain", "Внимание: лицензия/пробный период истекает через {rest}{until} — Enter/Клик: О программе/Активация · Esc / Скрыть / × до завтра", "Aviso: licencia/prueba caduca en {rest}{until} — Enter/Clic: Acerca de/Activar · Esc / Descartar / × hasta mañana", "注意：许可/试用将在 {rest} 后到期{until} — Enter/点击：关于/激活 · Esc / 忽略 / × 至明天", "Aviso: licença/teste expira em {rest}{until} — Enter/Clique: Sobre/Ativar · Esc / Dispensar / × até amanhã", "تنبيه: تنتهي الرخصة/التجربة خلال {rest}{until} — Enter/نقرة: حول/تفعيل · Esc / تجاهل / × حتى الغد", "Avviso: licenza/prova scade tra {rest}{until} — Invio/Clic: Info/Attiva · Esc / Ignora / × fino a domani"),
    ("expiry_expired_banner", "Lizenz abgelaufen{until} — Enter/Klick: Info/Aktivierung · Esc / Dismiss / × bis morgen", "License expired{until} — Enter/Click: About/Activate · Esc / Dismiss / × until tomorrow", "Licence expirée{until} — Entrée/Clic : À propos/Activer · Échap / Ignorer / × jusqu'à demain", "Лицензия истекла{until} — Enter/Клик: О программе/Активация · Esc / Скрыть / × до завтра", "Licencia caducada{until} — Enter/Clic: Acerca de/Activar · Esc / Descartar / × hasta mañana", "许可已过期{until} — Enter/点击：关于/激活 · Esc / 忽略 / × 至明天", "Licença expirada{until} — Enter/Clique: Sobre/Ativar · Esc / Dispensar / × até amanhã", "انتهت الرخصة{until} — Enter/نقرة: حول/تفعيل · Esc / تجاهل / × حتى الغد", "Licenza scaduta{until} — Invio/Clic: Info/Attiva · Esc / Ignora / × fino a domani"),
    ("expiry_warn_tooltip", "Enter/Klick öffnet Info / Lizenz aktivieren; Esc schließt; Fokus-Ring", "Enter/Click opens About / activate license; Esc dismisses; focus ring", "Entrée/Clic ouvre À propos / activer la licence ; Échap ferme ; anneau de focus", "Enter/Клик открывает О программе / активацию; Esc закрывает; кольцо фокуса", "Enter/Clic abre Acerca de / activar licencia; Esc cierra; anillo de foco", "Enter/点击打开关于/激活许可；Esc 关闭；焦点环", "Enter/Clique abre Sobre / ativar licença; Esc fecha; anel de foco", "Enter/نقرة تفتح حول / تفعيل الرخصة؛ Esc يغلق؛ حلقة التركيز", "Invio/Clic apre Info / attiva licenza; Esc chiude; anello di focus"),
    ("expiry_dismiss_label", "Dismiss", "Dismiss", "Ignorer", "Скрыть", "Descartar", "忽略", "Dispensar", "تجاهل", "Ignora"),
    ("expiry_dismiss_tooltip", "Hinweis schließen — dismiss_date bis morgen", "Dismiss notice — dismiss_date until tomorrow", "Fermer l'avis — dismiss_date jusqu'à demain", "Скрыть уведомление — dismiss_date до завтра", "Cerrar aviso — dismiss_date hasta mañana", "关闭提示 — dismiss_date 至明天", "Fechar aviso — dismiss_date até amanhã", "إغلاق التنبيه — dismiss_date حتى الغد", "Chiudi avviso — dismiss_date fino a domani"),
    ("expiry_close_tooltip", "Schließen (×) — Hinweis bis morgen ausblenden", "Close (×) — hide notice until tomorrow", "Fermer (×) — masquer l'avis jusqu'à demain", "Закрыть (×) — скрыть уведомление до завтра", "Cerrar (×) — ocultar aviso hasta mañana", "关闭 (×) — 隐藏提示至明天", "Fechar (×) — ocultar aviso até amanhã", "إغلاق (×) — إخفاء التنبيه حتى الغد", "Chiudi (×) — nascondi avviso fino a domani"),
    ("expiry_dismiss_status", "Ablauf-Hinweis bis morgen ausgeblendet", "Expiry notice hidden until tomorrow", "Avis d'expiration masqué jusqu'à demain", "Уведомление об истечении скрыто до завтра", "Aviso de caducidad oculto hasta mañana", "到期提示已隐藏至明天", "Aviso de expiração oculto até amanhã", "تنبيه الانتهاء مخفي حتى الغد", "Avviso scadenza nascosto fino a domani"),
    ("expiry_banner_accessible", "Lizenz-Ablaufhinweis", "License expiry notice", "Avis d'expiration de licence", "Уведомление об истечении лицензии", "Aviso de caducidad de licencia", "许可到期提示", "Aviso de expiração da licença", "تنبيه انتهاء الرخصة", "Avviso scadenza licenza"),
    ("expiry_banner_expired_accessible", "Lizenz abgelaufen — Hinweisbanner", "License expired — notice banner", "Licence expirée — bannière", "Лицензия истекла — баннер", "Licencia caducada — banner", "许可已过期 — 横幅", "Licença expirada — banner", "انتهت الرخصة — شعار تنبيه", "Licenza scaduta — banner"),
    ("expiry_banner_icon_accessible", "Warnsymbol Lizenzablauf", "License expiry warning icon", "Icône d'avertissement d'expiration", "Значок предупреждения об истечении", "Icono de advertencia de caducidad", "许可到期警告图标", "Ícone de aviso de expiração", "أيقونة تحذير انتهاء الرخصة", "Icona avviso scadenza licenza"),
    ("expiry_dismiss_accessible", "Ablaufhinweis schließen (Dismiss)", "Dismiss expiry notice", "Fermer l'avis d'expiration", "Скрыть уведомление об истечении", "Descartar aviso de caducidad", "关闭到期提示", "Dispensar aviso de expiração", "تجاهل تنبيه الانتهاء", "Ignora avviso scadenza"),
    ("expiry_close_accessible", "Ablaufhinweis schließen", "Close expiry notice", "Fermer l'avis d'expiration", "Закрыть уведомление об истечении", "Cerrar aviso de caducidad", "关闭到期提示", "Fechar aviso de expiração", "إغلاق تنبيه الانتهاء", "Chiudi avviso scadenza"),
    ("ann_zero_filtered", "Keine gefilterten Treffer auf Seite {page}", "No filtered matches on page {page}", "Aucun résultat filtré à la page {page}", "Нет отфильтрованных совпадений на странице {page}", "Sin coincidencias filtradas en la página {page}", "第 {page} 页无筛选匹配", "Sem correspondências filtradas na página {page}", "لا نتائج مُصفّاة في الصفحة {page}", "Nessuna corrispondenza filtrata a pagina {page}"),
    # Module / menus
    ("menu_file", "&Datei", "&File", "&Fichier", "&Файл", "&Archivo", "文件(&F)", "&Ficheiro", "&ملف", "&File"),
    ("menu_edit", "&Bearbeiten", "&Edit", "&Édition", "&Правка", "&Editar", "编辑(&E)", "&Editar", "&تحرير", "&Modifica"),
    ("menu_view", "&Ansicht", "&View", "&Affichage", "&Вид", "&Ver", "视图(&V)", "&Ver", "&عرض", "&Visualizza"),
    ("menu_pdf", "&PDF", "&PDF", "&PDF", "&PDF", "&PDF", "PDF(&P)", "&PDF", "&PDF", "&PDF"),
    ("menu_insert", "&Einfügen", "&Insert", "&Insertion", "&Вставка", "&Insertar", "插入(&I)", "&Inserir", "&إدراج", "&Inserisci"),
    ("menu_extras", "E&xtras", "E&xtras", "E&xtras", "Дополнительно", "E&xtras", "附加(&X)", "E&xtras", "إ&ضافات", "E&xtra"),
    ("menu_help", "&Hilfe", "&Help", "&Aide", "&Справка", "&Ayuda", "帮助(&H)", "&Ajuda", "&مساعدة", "&Aiuto"),
    ("menu_new", "Neu", "New", "Nouveau", "Создать", "Nuevo", "新建", "Novo", "جديد", "Nuovo"),
    ("menu_export", "Exportieren", "Export", "Exporter", "Экспорт", "Exportar", "导出", "Exportar", "تصدير", "Esporta"),
    ("action_open", "Öffnen…", "Open…", "Ouvrir…", "Открыть…", "Abrir…", "打开…", "Abrir…", "فتح…", "Apri…"),
    ("action_save", "Speichern", "Save", "Enregistrer", "Сохранить", "Guardar", "保存", "Guardar", "حفظ", "Salva"),
    ("action_save_as", "Speichern unter…", "Save as…", "Enregistrer sous…", "Сохранить как…", "Guardar como…", "另存为…", "Guardar como…", "حفظ باسم…", "Salva con nome…"),
    ("action_save_all", "Alles speichern", "Save all", "Tout enregistrer", "Сохранить всё", "Guardar todo", "全部保存", "Guardar tudo", "حفظ الكل", "Salva tutto"),
    ("action_close", "Schließen", "Close", "Fermer", "Закрыть", "Cerrar", "关闭", "Fechar", "إغلاق", "Chiudi"),
    ("action_quit", "Beenden", "Quit", "Quitter", "Выход", "Salir", "退出", "Sair", "خروج", "Esci"),
    ("action_print", "Drucken…", "Print…", "Imprimer…", "Печать…", "Imprimir…", "打印…", "Imprimir…", "طباعة…", "Stampa…"),
    ("action_undo", "Rückgängig", "Undo", "Annuler", "Отменить", "Deshacer", "撤销", "Anular", "تراجع", "Annulla"),
    ("action_redo", "Wiederholen", "Redo", "Rétablir", "Повторить", "Rehacer", "重做", "Refazer", "إعادة", "Ripeti"),
    ("action_find", "Suchen…", "Find…", "Rechercher…", "Найти…", "Buscar…", "查找…", "Localizar…", "بحث…", "Trova…"),
    ("action_find_replace", "Suchen und Ersetzen…", "Find and replace…", "Rechercher et remplacer…", "Найти и заменить…", "Buscar y reemplazar…", "查找和替换…", "Localizar e substituir…", "بحث واستبدال…", "Trova e sostituisci…"),
    ("action_settings", "Einstellungen…", "Settings…", "Paramètres…", "Настройки…", "Ajustes…", "设置…", "Definições…", "الإعدادات…", "Impostazioni…"),
    ("action_ocr", "OCR (Bild/PDF-Seite)…", "OCR (image/PDF page)…", "OCR (image/page PDF)…", "OCR (изображение/страница PDF)…", "OCR (imagen/página PDF)…", "OCR（图像/PDF 页）…", "OCR (imagem/página PDF)…", "OCR (صورة/صفحة PDF)…", "OCR (immagine/pagina PDF)…"),
    ("action_ocr_doc", "OCR gesamtes PDF…", "OCR entire PDF…", "OCR PDF entier…", "OCR всего PDF…", "OCR PDF completo…", "OCR 整个 PDF…", "OCR PDF completo…", "OCR لملف PDF بالكامل…", "OCR PDF intero…"),
    ("action_ocr_region", "OCR Region (Rechteck)…", "OCR region (rectangle)…", "OCR région (rectangle)…", "OCR область (прямоугольник)…", "OCR región (rectángulo)…", "OCR 区域（矩形）…", "OCR região (retângulo)…", "OCR منطقة (مستطيل)…", "OCR regione (rettangolo)…"),
    ("action_ocr_word_suite", "In Word-Suite öffnen/übernehmen…", "Open/import into Word Suite…", "Ouvrir/importer dans Word Suite…", "Открыть/перенести в Word Suite…", "Abrir/importar en Word Suite…", "在 Word 套件中打开/导入…", "Abrir/importar na Word Suite…", "فتح/استيراد إلى Word Suite…", "Apri/importa in Word Suite…"),
    ("action_ki_wizard", "Dokument erstellen… (KI-Wizard)", "Create document… (AI wizard)", "Créer un document… (assistant IA)", "Создать документ… (ИИ-мастер)", "Crear documento… (asistente IA)", "创建文档…（AI 向导）", "Criar documento… (assistente IA)", "إنشاء مستند… (معالج الذكاء الاصطناعي)", "Crea documento… (procedura guidata IA)"),
    ("action_forms", "Formulargenerator…", "Form generator…", "Générateur de formulaires…", "Генератор форм…", "Generador de formularios…", "表单生成器…", "Gerador de formulários…", "مولّد النماذج…", "Generatore di moduli…"),
    ("action_scan", "Scannen / Import…", "Scan / Import…", "Numériser / Importer…", "Сканировать / Импорт…", "Escanear / Importar…", "扫描 / 导入…", "Digitalizar / Importar…", "مسح / استيراد…", "Scansione / Importa…"),
    ("action_batch", "Batch-Konvertierung (Ordner)…", "Batch conversion (folder)…", "Conversion par lots (dossier)…", "Пакетное преобразование (папка)…", "Conversión por lotes (carpeta)…", "批量转换（文件夹）…", "Conversão em lote (pasta)…", "تحويل دفعي (مجلد)…", "Conversione batch (cartella)…"),
    ("action_help", "Hilfe…", "Help…", "Aide…", "Справка…", "Ayuda…", "帮助…", "Ajuda…", "مساعدة…", "Aiuto…"),
    ("action_about", "Info…", "About…", "À propos…", "О программе…", "Acerca de…", "关于…", "Sobre…", "حول…", "Informazioni…"),
    ("action_getting_started", "Erste Schritte…", "Getting started…", "Premiers pas…", "Первые шаги…", "Primeros pasos…", "入门…", "Primeiros passos…", "الخطوات الأولى…", "Primi passi…"),
    ("action_keyboard", "Tastatur-Cheat-Sheet…", "Keyboard cheat sheet…", "Aide-mémoire clavier…", "Шпаргалка клавиш…", "Hoja de atajos…", "键盘速查表…", "Folha de atalhos…", "ورقة اختصارات…", "Promemoria tastiera…"),
    ("action_handwriting", "Handschriftenerkennung…", "Handwriting recognition…", "Reconnaissance d'écriture…", "Распознавание рукописи…", "Reconocimiento de escritura…", "手写识别…", "Reconhecimento de escrita…", "التعرّف على الكتابة اليدوية…", "Riconoscimento scrittura…"),
    ("module_viewer", "Viewer", "Viewer", "Visionneuse", "Просмотр", "Visor", "查看器", "Visualizador", "العارض", "Visualizzatore"),
    ("module_ocr", "OCR", "OCR", "OCR", "OCR", "OCR", "OCR", "OCR", "OCR", "OCR"),
    ("module_scan", "Scan", "Scan", "Numérisation", "Скан", "Escaneo", "扫描", "Digitalização", "مسح", "Scansione"),
    ("module_annotations", "Annotationen", "Annotations", "Annotations", "Аннотации", "Anotaciones", "注释", "Anotações", "التعليقات التوضيحية", "Annotazioni"),
    ("module_forms", "Formulare", "Forms", "Formulaires", "Формы", "Formularios", "表单", "Formulários", "النماذج", "Moduli"),
    ("module_export", "Export", "Export", "Export", "Экспорт", "Exportación", "导出", "Exportação", "تصدير", "Esportazione"),
    ("module_wizards", "Assistenten", "Wizards", "Assistants", "Мастера", "Asistentes", "向导", "Assistentes", "المعالجات", "Procedure guidate"),
    ("module_settings", "Einstellungen", "Settings", "Paramètres", "Настройки", "Ajustes", "设置", "Definições", "الإعدادات", "Impostazioni"),
    ("help_tab_usage", "Bedienung", "Usage", "Utilisation", "Использование", "Uso", "用法", "Utilização", "الاستخدام", "Uso"),
    ("help_tab_features", "Features", "Features", "Fonctionnalités", "Возможности", "Funciones", "功能", "Funcionalidades", "الميزات", "Funzionalità"),
    ("help_open_logs", "Logordner öffnen", "Open log folder", "Ouvrir le dossier des journaux", "Открыть папку журналов", "Abrir carpeta de registros", "打开日志文件夹", "Abrir pasta de registos", "فتح مجلد السجلات", "Apri cartella log"),
    ("help_crash_report", "Crash-Report…", "Crash report…", "Rapport de plantage…", "Отчёт о сбое…", "Informe de fallo…", "崩溃报告…", "Relatório de falha…", "تقرير الأعطال…", "Report crash…"),
    ("lang_changed", "Oberflächensprache geändert — UI wird aktualisiert.", "UI language changed — interface updating.", "Langue de l'interface modifiée — mise à jour de l'UI.", "Язык интерфейса изменён — интерфейс обновляется.", "Idioma de la interfaz cambiado — actualizando la UI.", "界面语言已更改 — 正在更新界面。", "Idioma da interface alterado — a atualizar a UI.", "تم تغيير لغة الواجهة — جارٍ تحديث الواجهة.", "Lingua interfaccia modificata — aggiornamento UI."),
    ("lang_restart_hint", "Einige Dialoge übernehmen die Sprache beim nächsten Öffnen.", "Some dialogs apply the language the next time they open.", "Certains dialogues appliquent la langue à la prochaine ouverture.", "Некоторые диалоги применят язык при следующем открытии.", "Algunos diálogos aplican el idioma la próxima vez que se abran.", "部分对话框将在下次打开时应用语言。", "Alguns diálogos aplicam o idioma na próxima abertura.", "بعض الحوارات تطبّق اللغة عند الفتح التالي.", "Alcuni dialoghi applicano la lingua alla prossima apertura."),
    ("handwriting_title", "Handschriftenerkennung", "Handwriting recognition", "Reconnaissance d'écriture manuscrite", "Распознавание рукописного текста", "Reconocimiento de escritura manuscrita", "手写识别", "Reconhecimento de escrita manuscrita", "التعرّف على الكتابة اليدوية", "Riconoscimento della scrittura"),
    ("handwriting_hint", "Basis-Hook: Tesseract PSM für Handschrift/kurze Zeilen. Kein separates ML-Modell.", "Basic hook: Tesseract PSM for handwriting/short lines. No separate ML model.", "Hook de base : PSM Tesseract pour écriture/lignes courtes. Pas de modèle ML séparé.", "Базовый хук: Tesseract PSM для рукописи/коротких строк. Без отдельной ML-модели.", "Gancho básico: PSM de Tesseract para escritura/líneas cortas. Sin modelo ML aparte.", "基础挂钩：用于手写/短行的 Tesseract PSM。无独立 ML 模型。", "Hook básico: PSM Tesseract para escrita/linhas curtas. Sem modelo ML separado.", "خطاف أساسي: PSM من Tesseract للكتابة/الأسطر القصيرة. بلا نموذج ML منفصل.", "Hook di base: PSM Tesseract per scrittura/righe corte. Nessun modello ML separato."),
    ("handwriting_mode", "Handschrift-Modus (PSM)", "Handwriting mode (PSM)", "Mode écriture (PSM)", "Режим рукописи (PSM)", "Modo escritura (PSM)", "手写模式 (PSM)", "Modo escrita (PSM)", "وضع الكتابة اليدوية (PSM)", "Modalità scrittura (PSM)"),
    ("rtl_active", "RTL-Layout aktiv (Arabisch)", "RTL layout active (Arabic)", "Disposition RTL active (arabe)", "RTL-разметка активна (арабский)", "Diseño RTL activo (árabe)", "RTL 布局已启用（阿拉伯语）", "Layout RTL ativo (árabe)", "تخطيط RTL نشط (العربية)", "Layout RTL attivo (arabo)"),
    ("info_version", "Version", "Version", "Version", "Версия", "Versión", "版本", "Versão", "الإصدار", "Versione"),
    ("info_vendor", "Hersteller", "Vendor", "Éditeur", "Производитель", "Fabricante", "厂商", "Fabricante", "الشركة المصنعة", "Produttore"),
    ("info_contact", "Kontakt", "Contact", "Contact", "Контакт", "Contacto", "联系", "Contacto", "التواصل", "Contatto"),
    ("info_privacy", "Privacy: lokal, keine Telemetrie", "Privacy: local, no telemetry", "Confidentialité : local, pas de télémétrie", "Конфиденциальность: локально, без телеметрии", "Privacidad: local, sin telemetría", "隐私：本地，无遥测", "Privacidade: local, sem telemetria", "الخصوصية: محلي، بلا قياس عن بُعد", "Privacy: locale, nessuna telemetria"),
    ("features_missing", "FEATURES.md nicht gefunden.", "FEATURES.md not found.", "FEATURES.md introuvable.", "FEATURES.md не найден.", "FEATURES.md no encontrado.", "未找到 FEATURES.md。", "FEATURES.md não encontrado.", "FEATURES.md غير موجود.", "FEATURES.md non trovato."),
    ("installer_desktop_icon", "Desktop-Verknüpfung erstellen", "Create a desktop shortcut", "Créer un raccourci bureau", "Создать ярлык на рабочем столе", "Crear acceso directo en el escritorio", "创建桌面快捷方式", "Criar atalho no ambiente de trabalho", "إنشاء اختصار على سطح المكتب", "Crea collegamento sul desktop"),
    ("installer_start_menu", "Einträge im Startmenü belassen", "Keep Start Menu entries", "Conserver les entrées du menu Démarrer", "Оставить пункты в меню Пуск", "Mantener entradas del menú Inicio", "保留开始菜单项", "Manter entradas no menu Iniciar", "الإبقاء على إدخالات قائمة ابدأ", "Mantieni voci nel menu Start"),
    ("installer_launch_now", "InstantLens Doc jetzt starten", "Launch InstantLens Doc now", "Lancer InstantLens Doc maintenant", "Запустить InstantLens Doc сейчас", "Iniciar InstantLens Doc ahora", "立即启动 InstantLens Doc", "Iniciar InstantLens Doc agora", "تشغيل InstantLens Doc الآن", "Avvia InstantLens Doc ora"),
    ("installer_build_hint", "Setup.exe (Windows x64): powershell -ExecutionPolicy Bypass -File .\\scripts\\build-windows-installer.ps1", "Setup.exe (Windows x64): powershell -ExecutionPolicy Bypass -File .\\scripts\\build-windows-installer.ps1", "Setup.exe (Windows x64) : powershell -ExecutionPolicy Bypass -File .\\scripts\\build-windows-installer.ps1", "Setup.exe (Windows x64): powershell -ExecutionPolicy Bypass -File .\\scripts\\build-windows-installer.ps1", "Setup.exe (Windows x64): powershell -ExecutionPolicy Bypass -File .\\scripts\\build-windows-installer.ps1", "Setup.exe (Windows x64)：powershell -ExecutionPolicy Bypass -File .\\scripts\\build-windows-installer.ps1", "Setup.exe (Windows x64): powershell -ExecutionPolicy Bypass -File .\\scripts\\build-windows-installer.ps1", "Setup.exe (Windows x64): powershell -ExecutionPolicy Bypass -File .\\scripts\\build-windows-installer.ps1", "Setup.exe (Windows x64): powershell -ExecutionPolicy Bypass -File .\\scripts\\build-windows-installer.ps1"),
]

# Phrase map: German UI source → translations (for tree retranslate)
PHRASES: list[tuple[str, ...]] = [
    ("&Datei", "&File", "&Fichier", "&Файл", "&Archivo", "文件(&F)", "&Ficheiro", "&ملف", "&File"),
    ("Datei", "File", "Fichier", "Файл", "Archivo", "文件", "Ficheiro", "ملف", "File"),
    ("&Bearbeiten", "&Edit", "&Édition", "&Правка", "&Editar", "编辑(&E)", "&Editar", "&تحرير", "&Modifica"),
    ("Bearbeiten", "Edit", "Édition", "Правка", "Editar", "编辑", "Editar", "تحرير", "Modifica"),
    ("&Ansicht", "&View", "&Affichage", "&Вид", "&Ver", "视图(&V)", "&Ver", "&عرض", "&Visualizza"),
    ("Ansicht", "View", "Affichage", "Вид", "Ver", "视图", "Ver", "عرض", "Visualizza"),
    ("&PDF", "&PDF", "&PDF", "&PDF", "&PDF", "PDF(&P)", "&PDF", "&PDF", "&PDF"),
    ("&Einfügen", "&Insert", "&Insertion", "&Вставка", "&Insertar", "插入(&I)", "&Inserir", "&إدراج", "&Inserisci"),
    ("Einfügen", "Insert", "Insertion", "Вставка", "Insertar", "插入", "Inserir", "إدراج", "Inserisci"),
    ("E&xtras", "E&xtras", "E&xtras", "Дополнительно", "E&xtras", "附加(&X)", "E&xtras", "إ&ضافات", "E&xtra"),
    ("&Hilfe", "&Help", "&Aide", "&Справка", "&Ayuda", "帮助(&H)", "&Ajuda", "&مساعدة", "&Aiuto"),
    ("Hilfe", "Help", "Aide", "Справка", "Ayuda", "帮助", "Ajuda", "مساعدة", "Aiuto"),
    ("Neu", "New", "Nouveau", "Создать", "Nuevo", "新建", "Novo", "جديد", "Nuovo"),
    ("Leeres Dokument", "Blank document", "Document vide", "Пустой документ", "Documento en blanco", "空白文档", "Documento em branco", "مستند فارغ", "Documento vuoto"),
    ("Brief…", "Letter…", "Lettre…", "Письмо…", "Carta…", "信函…", "Carta…", "رسالة…", "Lettera…"),
    ("Notiz…", "Note…", "Note…", "Заметка…", "Nota…", "便签…", "Nota…", "ملاحظة…", "Nota…"),
    ("Öffnen…", "Open…", "Ouvrir…", "Открыть…", "Abrir…", "打开…", "Abrir…", "فتح…", "Apri…"),
    ("Speichern", "Save", "Enregistrer", "Сохранить", "Guardar", "保存", "Guardar", "حفظ", "Salva"),
    ("Speichern unter…", "Save as…", "Enregistrer sous…", "Сохранить как…", "Guardar como…", "另存为…", "Guardar como…", "حفظ باسم…", "Salva con nome…"),
    ("Alles speichern", "Save all", "Tout enregistrer", "Сохранить всё", "Guardar todo", "全部保存", "Guardar tudo", "حفظ الكل", "Salva tutto"),
    ("Als Kopie speichern…", "Save as copy…", "Enregistrer une copie…", "Сохранить копию…", "Guardar como copia…", "另存为副本…", "Guardar como cópia…", "حفظ كنسخة…", "Salva come copia…"),
    ("Schließen", "Close", "Fermer", "Закрыть", "Cerrar", "关闭", "Fechar", "إغلاق", "Chiudi"),
    ("Andere Tabs schließen", "Close other tabs", "Fermer les autres onglets", "Закрыть другие вкладки", "Cerrar otras pestañas", "关闭其他标签", "Fechar outros separadores", "إغلاق علامات التبويب الأخرى", "Chiudi altre schede"),
    ("Alle Tabs schließen", "Close all tabs", "Fermer tous les onglets", "Закрыть все вкладки", "Cerrar todas las pestañas", "关闭所有标签", "Fechar todos os separadores", "إغلاق كل علامات التبويب", "Chiudi tutte le schede"),
    ("Beenden", "Quit", "Quitter", "Выход", "Salir", "退出", "Sair", "خروج", "Esci"),
    ("Drucken…", "Print…", "Imprimer…", "Печать…", "Imprimir…", "打印…", "Imprimir…", "طباعة…", "Stampa…"),
    ("Exportieren", "Export", "Exporter", "Экспорт", "Exportar", "导出", "Exportar", "تصدير", "Esporta"),
    ("Rückgängig", "Undo", "Annuler", "Отменить", "Deshacer", "撤销", "Anular", "تراجع", "Annulla"),
    ("Wiederholen", "Redo", "Rétablir", "Повторить", "Rehacer", "重做", "Refazer", "إعادة", "Ripeti"),
    ("Suchen…", "Find…", "Rechercher…", "Найти…", "Buscar…", "查找…", "Localizar…", "بحث…", "Trova…"),
    ("Weitersuchen", "Find next", "Rechercher suivant", "Найти далее", "Buscar siguiente", "查找下一个", "Localizar seguinte", "بحث عن التالي", "Trova successivo"),
    ("Rückwärtssuchen", "Find previous", "Rechercher précédent", "Найти ранее", "Buscar anterior", "查找上一个", "Localizar anterior", "بحث عن السابق", "Trova precedente"),
    ("Suchen und Ersetzen…", "Find and replace…", "Rechercher et remplacer…", "Найти и заменить…", "Buscar y reemplazar…", "查找和替换…", "Localizar e substituir…", "بحث واستبدال…", "Trova e sostituisci…"),
    ("Fett", "Bold", "Gras", "Жирный", "Negrita", "粗体", "Negrito", "غامق", "Grassetto"),
    ("Kursiv", "Italic", "Italique", "Курсив", "Cursiva", "斜体", "Itálico", "مائل", "Corsivo"),
    ("Unterstrichen", "Underline", "Souligné", "Подчёркнутый", "Subrayado", "下划线", "Sublinhado", "تسطير", "Sottolineato"),
    ("Einstellungen…", "Settings…", "Paramètres…", "Настройки…", "Ajustes…", "设置…", "Definições…", "الإعدادات…", "Impostazioni…"),
    ("Einstellungen", "Settings", "Paramètres", "Настройки", "Ajustes", "设置", "Definições", "الإعدادات", "Impostazioni"),
    ("OCR (Bild/PDF-Seite)…", "OCR (image/PDF page)…", "OCR (image/page PDF)…", "OCR (изображение/страница PDF)…", "OCR (imagen/página PDF)…", "OCR（图像/PDF 页）…", "OCR (imagem/página PDF)…", "OCR (صورة/صفحة PDF)…", "OCR (immagine/pagina PDF)…"),
    ("OCR gesamtes PDF…", "OCR entire PDF…", "OCR PDF entier…", "OCR всего PDF…", "OCR PDF completo…", "OCR 整个 PDF…", "OCR PDF completo…", "OCR لملف PDF بالكامل…", "OCR PDF intero…"),
    ("OCR Region (Rechteck)…", "OCR region (rectangle)…", "OCR région (rectangle)…", "OCR область (прямоугольник)…", "OCR región (rectángulo)…", "OCR 区域（矩形）…", "OCR região (retângulo)…", "OCR منطقة (مستطيل)…", "OCR regione (rettangolo)…"),
    ("In Word-Suite öffnen/übernehmen…", "Open/import into Word Suite…", "Ouvrir/importer dans Word Suite…", "Открыть/перенести в Word Suite…", "Abrir/importar en Word Suite…", "在 Word 套件中打开/导入…", "Abrir/importar na Word Suite…", "فتح/استيراد إلى Word Suite…", "Apri/importa in Word Suite…"),
    ("Dokument erstellen… (KI-Wizard)", "Create document… (AI wizard)", "Créer un document… (assistant IA)", "Создать документ… (ИИ-мастер)", "Crear documento… (asistente IA)", "创建文档…（AI 向导）", "Criar documento… (assistente IA)", "إنشاء مستند… (معالج الذكاء الاصطناعي)", "Crea documento… (procedura guidata IA)"),
    ("Formulargenerator…", "Form generator…", "Générateur de formulaires…", "Генератор форм…", "Generador de formularios…", "表单生成器…", "Gerador de formulários…", "مولّد النماذج…", "Generatore di moduli…"),
    ("Batch-Konvertierung (Ordner)…", "Batch conversion (folder)…", "Conversion par lots (dossier)…", "Пакетное преобразование (папка)…", "Conversión por lotes (carpeta)…", "批量转换（文件夹）…", "Conversão em lote (pasta)…", "تحويل دفعي (مجلد)…", "Conversione batch (cartella)…"),
    ("Batch-Umbenennen (offene Tabs)…", "Batch rename (open tabs)…", "Renommage par lots (onglets ouverts)…", "Пакетное переименование (открытые вкладки)…", "Renombrar por lotes (pestañas abiertas)…", "批量重命名（打开的标签）…", "Renomear em lote (separadores abertos)…", "إعادة تسمية دُفعية (علامات مفتوحة)…", "Rinomina batch (schede aperte)…"),
    ("Handschriftenerkennung…", "Handwriting recognition…", "Reconnaissance d'écriture…", "Распознавание рукописи…", "Reconocimiento de escritura…", "手写识别…", "Reconhecimento de escrita…", "التعرّف على الكتابة اليدوية…", "Riconoscimento scrittura…"),
    ("Erste Schritte…", "Getting started…", "Premiers pas…", "Первые шаги…", "Primeros pasos…", "入门…", "Primeiros passos…", "الخطوات الأولى…", "Primi passi…"),
    ("Tastatur-Cheat-Sheet…", "Keyboard cheat sheet…", "Aide-mémoire clavier…", "Шпаргалка клавиш…", "Hoja de atajos…", "键盘速查表…", "Folha de atalhos…", "ورقة اختصارات…", "Promemoria tastiera…"),
    ("Hilfe…", "Help…", "Aide…", "Справка…", "Ayuda…", "帮助…", "Ajuda…", "مساعدة…", "Aiuto…"),
    ("Info…", "About…", "À propos…", "О программе…", "Acerca de…", "关于…", "Sobre…", "حول…", "Informazioni…"),
    ("Logordner öffnen", "Open log folder", "Ouvrir le dossier des journaux", "Открыть папку журналов", "Abrir carpeta de registros", "打开日志文件夹", "Abrir pasta de registos", "فتح مجلد السجلات", "Apri cartella log"),
    ("Crash-Report erstellen…", "Create crash report…", "Créer un rapport de plantage…", "Создать отчёт о сбое…", "Crear informe de fallo…", "创建崩溃报告…", "Criar relatório de falha…", "إنشاء تقرير أعطال…", "Crea report crash…"),
    ("Crash-Report…", "Crash report…", "Rapport de plantage…", "Отчёт о сбое…", "Informe de fallo…", "崩溃报告…", "Relatório de falha…", "تقرير الأعطال…", "Report crash…"),
    ("Jetzt prüfen…", "Check now…", "Vérifier maintenant…", "Проверить сейчас…", "Comprobar ahora…", "立即检查…", "Verificar agora…", "تحقق الآن…", "Controlla ora…"),
    ("Auf Updates prüfen…", "Check for updates…", "Rechercher des mises à jour…", "Проверить обновления…", "Buscar actualizaciones…", "检查更新…", "Procurar atualizações…", "البحث عن تحديثات…", "Controlla aggiornamenti…"),
    ("Zuletzt geöffnet", "Recently opened", "Ouverts récemment", "Недавние", "Abiertos recientemente", "最近打开", "Abertos recentemente", "فُتحت مؤخرًا", "Aperti di recente"),
    ("Projekt-Ordner", "Project folder", "Dossier projet", "Папка проекта", "Carpeta del proyecto", "项目文件夹", "Pasta do projeto", "مجلد المشروع", "Cartella progetto"),
    ("Meine Vorlagen", "My templates", "Mes modèles", "Мои шаблоны", "Mis plantillas", "我的模板", "Os meus modelos", "قوالبي", "I miei modelli"),
    ("Backup jetzt", "Backup now", "Sauvegarder maintenant", "Резервная копия сейчас", "Copia de seguridad ahora", "立即备份", "Cópia de segurança agora", "نسخ احتياطي الآن", "Backup ora"),
    ("Backup-Ordner öffnen…", "Open backup folder…", "Ouvrir le dossier de sauvegarde…", "Открыть папку резервных копий…", "Abrir carpeta de copias…", "打开备份文件夹…", "Abrir pasta de cópias…", "فتح مجلد النسخ الاحتياطي…", "Apri cartella backup…"),
    ("Erneut öffnen", "Reopen", "Rouvrir", "Открыть снова", "Reabrir", "重新打开", "Reabrir", "إعادة فتح", "Riapri"),
    ("Arbeitsverzeichnis öffnen", "Open working directory", "Ouvrir le répertoire de travail", "Открыть рабочий каталог", "Abrir directorio de trabajo", "打开工作目录", "Abrir diretório de trabalho", "فتح دليل العمل", "Apri directory di lavoro"),
    ("Annotationen", "Annotations", "Annotations", "Аннотации", "Anotaciones", "注释", "Anotações", "التعليقات التوضيحية", "Annotazioni"),
    ("Bedienung", "Usage", "Utilisation", "Использование", "Uso", "用法", "Utilização", "الاستخدام", "Uso"),
    ("Features", "Features", "Fonctionnalités", "Возможности", "Funciones", "功能", "Funcionalidades", "الميزات", "Funzionalità"),
    ("Oberflächensprache", "UI language", "Langue de l'interface", "Язык интерфейса", "Idioma de la interfaz", "界面语言", "Idioma da interface", "لغة الواجهة", "Lingua interfaccia"),
    ("Anzeigen", "Show", "Afficher", "Показать", "Mostrar", "显示", "Mostrar", "عرض", "Mostra"),
    ("Bildvorschau", "Image preview", "Aperçu image", "Просмотр изображения", "Vista previa de imagen", "图像预览", "Pré-visualização da imagem", "معاينة الصورة", "Anteprima immagine"),
    ("Zum Bearbeiten öffnen", "Open for editing", "Ouvrir pour édition", "Открыть для правки", "Abrir para editar", "打开以编辑", "Abrir para editar", "فتح للتحرير", "Apri per modificare"),
    ("KI-Assistent (geplant)", "AI assistant (planned)", "Assistant IA (prévu)", "ИИ-ассистент (планируется)", "Asistente IA (planificado)", "AI 助手（计划中）", "Assistente IA (planeado)", "مساعد الذكاء الاصطناعي (مخطط)", "Assistente IA (pianificato)"),
    ("Gemeinsames Review / Cloud-Ordner…", "Shared review / cloud folder…", "Revue partagée / dossier cloud…", "Совместный обзор / облачная папка…", "Revisión compartida / carpeta cloud…", "共享审阅 / 云文件夹…", "Revisão partilhada / pasta cloud…", "مراجعة مشتركة / مجلد سحابي…", "Revisione condivisa / cartella cloud…"),
    ("Cloud-Sync (geplant)", "Cloud sync (planned)", "Sync cloud (prévu)", "Облачная синхронизация (планируется)", "Sincronización en la nube (planificado)", "云同步（计划中）", "Sincronização na nuvem (planeado)", "مزامنة سحابية (مخطط)", "Sincronizzazione cloud (pianificata)"),
    ("Geplant", "Planned", "Prévu", "Запланировано", "Planificado", "计划中", "Planeado", "مخطط", "Pianificato"),
]


def pack_row(values: tuple[str, ...]) -> dict[str, str]:
    # values: de,en,fr,ru,es,zh,pt,ar,it
    return {lang: values[i] for i, lang in enumerate(LANGS)}


def main() -> None:
    strings: dict[str, dict[str, str]] = {}
    for row in ROWS:
        key = row[0]
        strings[key] = pack_row(row[1:])

    phrases: dict[str, dict[str, str]] = {}
    for row in PHRASES:
        de = row[0]
        # phrase map: de source -> all langs including de
        phrases[de] = pack_row(row)

    catalog = {
        "version": "2.6.27",
        "langs": list(LANGS),
        "rtl": ["ar"],
        "strings": strings,
        "phrases": phrases,
    }
    (LOC / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Per-language compact JSON for external tooling
    for lang in LANGS:
        slim = {
            "lang": lang,
            "rtl": lang == "ar",
            "strings": {k: v[lang] for k, v in strings.items()},
            "phrases": {k: v[lang] for k, v in phrases.items()},
        }
        (LOC / f"{lang}.json").write_text(
            json.dumps(slim, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    help_bodies = {
        "de": """<h2>InstantLens Doc — Hilfe</h2>
<p>Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.</p>
<p><b>Sprache:</b> Extras → Einstellungen → Oberflächensprache (DE, EN, FR, RU, ES, ZH, PT, AR, IT). Auswahl wird gespeichert. Arabisch aktiviert RTL wo praktikabel.</p>
<h3>Module</h3>
<ul>
<li><b>Viewer</b> — PDF/Text anzeigen, zoomen, Seiten</li>
<li><b>OCR</b> — Bild/PDF-Seite, Region, gesamtes PDF; optional Handschrift-PSM</li>
<li><b>Scan</b> — Import/Scanner + Tesseract</li>
<li><b>Annotationen</b> — Markieren, Stempel, Formen</li>
<li><b>Formulare</b> — AcroForm / Formulargenerator</li>
<li><b>Export</b> — HTML/DOCX/XLSX/PDF/TXT/RTF/JPG</li>
<li><b>Assistenten</b> — Erste Schritte, KI-Dokument-Wizards (kein freier Chat)</li>
<li><b>Einstellungen</b> — Theme, Sprache, OCR, Export, Autosave</li>
</ul>
<p>Vollständige Feature-Liste: FEATURES.md · Info: INFO.md</p>
""",
        "en": """<h2>InstantLens Doc — Help</h2>
<p>Modern document processing with PDF annotator, OCR bridge and form generator.</p>
<p><b>Language:</b> Extras → Settings → UI language (DE, EN, FR, RU, ES, ZH, PT, AR, IT). Choice is persisted. Arabic enables RTL where practical.</p>
<h3>Modules</h3>
<ul>
<li><b>Viewer</b> — view PDF/text, zoom, pages</li>
<li><b>OCR</b> — image/PDF page, region, entire PDF; optional handwriting PSM</li>
<li><b>Scan</b> — import/scanner + Tesseract</li>
<li><b>Annotations</b> — highlight, stamps, shapes</li>
<li><b>Forms</b> — AcroForm / form generator</li>
<li><b>Export</b> — HTML/DOCX/XLSX/PDF/TXT/RTF/JPG</li>
<li><b>Wizards</b> — Getting started, AI document wizards (no free chat)</li>
<li><b>Settings</b> — theme, language, OCR, export, autosave</li>
</ul>
<p>Full feature list: FEATURES.md · About: INFO.md</p>
""",
    }
    # Scaffold other languages with real key strings
    scaffolds = {
        "fr": ("Aide", "Langue", "Modules", "Visionneuse", "Paramètres", "Liste des fonctionnalités"),
        "ru": ("Справка", "Язык", "Модули", "Просмотр", "Настройки", "Список возможностей"),
        "es": ("Ayuda", "Idioma", "Módulos", "Visor", "Ajustes", "Lista de funciones"),
        "zh": ("帮助", "语言", "模块", "查看器", "设置", "功能列表"),
        "pt": ("Ajuda", "Idioma", "Módulos", "Visualizador", "Definições", "Lista de funcionalidades"),
        "ar": ("مساعدة", "اللغة", "الوحدات", "العارض", "الإعدادات", "قائمة الميزات"),
        "it": ("Aiuto", "Lingua", "Moduli", "Visualizzatore", "Impostazioni", "Elenco funzionalità"),
    }
    for lang, (help_t, lang_t, mod_t, view_t, set_t, feat_t) in scaffolds.items():
        dir_attr = ' dir="rtl"' if lang == "ar" else ""
        help_bodies[lang] = f"""<div{dir_attr}>
<h2>InstantLens Doc — {help_t}</h2>
<p><b>{lang_t}:</b> DE · EN · FR · RU · ES · ZH · PT · AR · IT — {set_t}.</p>
<h3>{mod_t}</h3>
<ul>
<li><b>{view_t}</b> · OCR · Scan · Annotations · Forms · Export · Wizards · {set_t}</li>
</ul>
<p>{feat_t}: FEATURES.md · INFO.md</p>
</div>
"""

    for lang, html in help_bodies.items():
        (HELP / f"{lang}.html").write_text(html.strip() + "\n", encoding="utf-8")

    print(f"Wrote catalog: {len(strings)} keys, {len(phrases)} phrases, help for {len(help_bodies)} langs")


if __name__ == "__main__":
    main()
