# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
#
# """
# SCRIPT DE DIAGNOSTIC - PERMISSIONS
# ----------------------------------
# Analyse tous les fichiers Python du projet pour trouver
# les références à 'permission' et 'user_permissions'.
# """
#
# import os
# import re
# import sys
# from pathlib import Path
# from collections import defaultdict
#
# # ============================================
# # CONFIGURATION
# # ============================================
#
# # Dossiers à ignorer
# IGNORE_DIRS = {
#     '.venv', 'venv', 'env', 'venv', 'env',
#     '__pycache__', '.git', '.idea', '.vscode',
#     'node_modules', 'dist', 'build', 'eggs',
#     'lib', 'include', 'bin', 'Lib', 'Scripts'
# }
#
# # Extensions à analyser
# EXTENSIONS = {'.py'}
#
#
# # ============================================
# # FONCTIONS
# # ============================================
#
# def analyze_file(filepath):
#     """Analyse un fichier Python pour trouver les références."""
#     results = {
#         'permission_classes': [],
#         'user_permissions': [],
#         'relationships': [],
#         'secondary_refs': [],
#         'imports': []
#     }
#
#     try:
#         with open(filepath, 'r', encoding='utf-8') as f:
#             content = f.read()
#             lines = content.split('\n')
#
#             for line_num, line in enumerate(lines, 1):
#                 # 1️⃣ Class Permission
#                 if re.search(r'^\s*class\s+Permission', line):
#                     results['permission_classes'].append(line_num)
#
#                 # 2️⃣ user_permissions (table ou variable)
#                 if 'user_permissions' in line:
#                     results['user_permissions'].append(line_num)
#
#                 # 3️⃣ db.relationship avec permissions
#                 if 'db.relationship' in line and 'permission' in line.lower():
#                     results['relationships'].append(line_num)
#
#                 # 4️⃣ secondary=user_permissions
#                 if 'secondary' in line and 'user_permissions' in line:
#                     results['secondary_refs'].append(line_num)
#
#                 # 5️⃣ Imports de Permission
#                 if re.search(r'from\s+.*import.*Permission', line):
#                     results['imports'].append(line_num)
#
#     except Exception as e:
#         print(f"⚠️ Erreur lecture {filepath}: {e}")
#
#     return results
#
#
# def scan_project(root_dir='.'):
#     """Scanne tout le projet."""
#
#     root_path = Path(root_dir).resolve()
#     results = defaultdict(lambda: {
#         'permission_classes': [],
#         'user_permissions': [],
#         'relationships': [],
#         'secondary_refs': [],
#         'imports': []
#     })
#
#     print("=" * 70)
#     print("🔍 DIAGNOSTIC DES PERMISSIONS")
#     print("=" * 70)
#     print(f"📂 Dossier: {root_path}")
#     print("=" * 70)
#     print()
#
#     total_files = 0
#
#     for filepath in root_path.rglob('*'):
#         # Ignorer les dossiers exclus
#         if any(ignore in filepath.parts for ignore in IGNORE_DIRS):
#             continue
#
#         # Vérifier l'extension
#         if filepath.suffix not in EXTENSIONS:
#             continue
#
#         # Analyser le fichier
#         rel_path = filepath.relative_to(root_path)
#         file_results = analyze_file(filepath)
#
#         # Compter les résultats
#         total = (len(file_results['permission_classes']) +
#                  len(file_results['user_permissions']) +
#                  len(file_results['relationships']) +
#                  len(file_results['secondary_refs']) +
#                  len(file_results['imports']))
#
#         if total > 0:
#             results[str(rel_path)] = file_results
#             total_files += 1
#
#     return results, total_files
#
#
# def display_results(results, total_files):
#     """Affiche les résultats."""
#
#     if not results:
#         print("✅ AUCUNE RÉFÉRENCE À 'permission' TROUVÉE !")
#         print("🎉 Votre projet est propre.")
#         return
#
#     print(f"📊 {total_files} fichier(s) contiennent des références")
#     print()
#
#     total_permission_classes = 0
#     total_user_permissions = 0
#     total_relationships = 0
#     total_secondary = 0
#     total_imports = 0
#
#     for filename, data in sorted(results.items()):
#         print(f"📄 {filename}")
#         print("-" * 50)
#
#         # 1️⃣ Class Permission
#         if data['permission_classes']:
#             count = len(data['permission_classes'])
#             total_permission_classes += count
#             print(
#                 f"   🔵 class Permission : {count} occurrence(s) - Lignes {', '.join(map(str, data['permission_classes']))}")
#
#         # 2️⃣ user_permissions
#         if data['user_permissions']:
#             count = len(data['user_permissions'])
#             total_user_permissions += count
#             print(
#                 f"   🟢 user_permissions : {count} occurrence(s) - Lignes {', '.join(map(str, data['user_permissions']))}")
#
#         # 3️⃣ Relationships
#         if data['relationships']:
#             count = len(data['relationships'])
#             total_relationships += count
#             print(f"   🟡 db.relationship : {count} occurrence(s) - Lignes {', '.join(map(str, data['relationships']))}")
#
#         # 4️⃣ secondary refs
#         if data['secondary_refs']:
#             count = len(data['secondary_refs'])
#             total_secondary += count
#             print(f"   🟠 secondary= : {count} occurrence(s) - Lignes {', '.join(map(str, data['secondary_refs']))}")
#
#         # 5️⃣ Imports
#         if data['imports']:
#             count = len(data['imports'])
#             total_imports += count
#             print(f"   🟣 Imports : {count} occurrence(s) - Lignes {', '.join(map(str, data['imports']))}")
#
#         print()
#
#     # ============================================
#     # RÉSUMÉ FINAL
#     # ============================================
#     print("=" * 70)
#     print("📈 RÉSUMÉ COMPLET")
#     print("=" * 70)
#     print(f"   🔵 class Permission          : {total_permission_classes}")
#     print(f"   🟢 user_permissions          : {total_user_permissions}")
#     print(f"   🟡 db.relationship           : {total_relationships}")
#     print(f"   🟠 secondary=                : {total_secondary}")
#     print(f"   🟣 Imports                   : {total_imports}")
#     print("-" * 70)
#     print(
#         f"   📊 TOTAL GÉNÉRAL             : {total_permission_classes + total_user_permissions + total_relationships + total_secondary + total_imports}")
#     print("=" * 70)
#
#     # Recommandations
#     print()
#     print("💡 RECOMMANDATIONS :")
#     print("-" * 70)
#
#     if total_user_permissions > 0 or total_secondary > 0:
#         print("⚠️  Vous avez encore des références à 'user_permissions'.")
#         print("   ➜ Supprimez-les de models.py")
#
#     if total_permission_classes > 1:
#         print("⚠️  Plusieurs classes 'Permission' trouvées.")
#         print("   ➜ Vérifiez qu'il n'y a pas de doublons")
#
#     if total_relationships > 0:
#         print("⚠️  Des relations db.relationship avec permissions existent.")
#         print("   ➜ Supprimez-les ou commentez-les temporairement")
#
#     if total_imports > 0:
#         print("⚠️  Des imports de Permission sont encore présents.")
#         print("   ➜ Supprimez-les de app.py et autres fichiers")
#
#     if (total_user_permissions == 0 and
#             total_secondary == 0 and
#             total_relationships == 0 and
#             total_imports == 0 and
#             total_permission_classes <= 1):
#         print("✅ ✅ ✅ TOUT EST PROPRE !")
#         print("   Vous pouvez déployer sans problème.")
#
#
# def main():
#     """Fonction principale."""
#
#     # Dossier à analyser (par défaut, le dossier courant)
#     root_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
#
#     if not os.path.exists(root_dir):
#         print(f"❌ Le dossier '{root_dir}' n'existe pas.")
#         sys.exit(1)
#
#     try:
#         results, total_files = scan_project(root_dir)
#         display_results(results, total_files)
#
#     except KeyboardInterrupt:
#         print("\n\n⏹️  Analyse interrompue par l'utilisateur.")
#         sys.exit(0)
#     except Exception as e:
#         print(f"\n❌ Erreur inattendue: {e}")
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)
#
#
# if __name__ == "__main__":
#     main()