import json
import os
from collections import defaultdict
from pathlib import Path


def create_category_mapping():
    """
    Создает точный маппинг 92 категорий в 6 основных групп
    """

    mapping = {
        # ========== НИКЕЛЕВЫЕ СПЛАВЫ (nickel_alloy) ==========
        'nickel_alloy': [
            'low alloyed nickel alloys',
            'nickel alloys',
            'nickel cast iron',
            'nickel powder',
            'prefabricated nickel',
            'copper-nickel alloys',
        ],

        # ========== ТИТАНОВЫЕ СПЛАВЫ (titanium_alloy) ==========
        'titanium_alloy': [
            'foundry titanium alloys',
            'technical titan',
            'wrought titanium alloys',
        ],

        # ========== АЛЮМИНИЕВЫЕ СПЛАВЫ (aluminum_alloy) ==========
        'aluminum_alloy': [
            'antifriction aluminum alloy',
            'foundry aluminum alloys',
            'primary aluminum',
            'technical aluminum',
            'wrought aluminum alloys',
        ],

        # ========== МЕДНЫЕ СПЛАВЫ (copper_alloy) ==========
        'copper_alloy': [
            'brass, pressure treated',
            'bronze, heatproof',
            'copper',
            'copper alloys',
            'copper, base powder. antifriction materials',
            'foundry brass',
            'foundry brass ingots',
            'pressure tin bronze',
            'pressureless bronze plated',
            'tin cast bronze',
            'tinless cast bronze',
        ],

        # ========== СТАЛИ (steel_alloy) ==========
        'steel_alloy': [
            'alloy tool steel',
            'alloyed structural steel',
            'bearing structural steel',
            'carbon tool steel',
            'carbonaceous quality structural steel',
            'carbonaceous structural steel of ordinary quality',
            'corrosion-resistant heat-resistant steel',
            'corrosion-resistant ordinary steel',
            'cryogenic structural steel',
            'die tool steel',
            'heat resistant high alloy steel',
            'heat resistant low alloy steel',
            'heat-resistant relaxation-resistant steel',
            'high speed tool steel',
            'high strength high alloy structural steel',
            'improved machinability structural steel',
            'low alloy structural steel for welded structures',
            'ordinary steel for castings',
            'roll tool steel',
            'spring-spring structural steel',
            'steel for building structures',
            'steel for casting with special properties',
            'steel for rail transport',
            'steel welding wire',
            'steels for shipbuilding',
            'sulfur electrotechnical steel',
            'unalloyed electrical steel',
            'corrosion-resistant alloys',  # некоторые коррозионностойкие - стали
        ],

        # ========== ДРУГИЕ (other) ==========
        'other': [
            'corrosion-resistant alloys',  # если не попали в стали
            'ductile iron',
            'foundry magnesium alloys',
            'gold jewelery',
            'gold, gold alloys',
            'gray cast iron',
            'heat resistant alloys',
            'high alloy cast iron',
            'iridium, iridium alloys',
            'iron base powder. antifriction materials',
            'lead',
            'lead antimony alloys',
            'lead babbit',
            'low alloy cast iron',
            'magnesium alloys with special properties',
            'magnetic hard precision alloys',
            'molybdenum',
            'molybdenum powder material',
            'nodular cast iron',
            'palladium, palladium alloys',
            'platinum, platinum alloy',
            'precision alloys superconducting',
            'primary magnesium',
            'rhodium, rhodium alloys',
            'silver',
            'silver, silver alloys',
            'soft magnetic precision alloys',
            'thermobimetals',
            'tin',
            'tin babbitt',
            'tin-lead solder',
            'vermicular graphite cast iron',
            'with given tcle',
            'with high electrical resistance',
            'with preset elastic properties',
            'wrought magnesium alloys',
            'zinc antifriction alloys',
            'zinc foundry alloys',
            'zinc is the primary',
            'zinc wrought alloys',
        ]
    }

    # Создаем обратный словарь для быстрого поиска
    reverse_mapping = {}
    for target, categories in mapping.items():
        for cat in categories:
            reverse_mapping[cat] = target

    return reverse_mapping


def split_alloys_by_category(input_file='aloro/data_cleaned.json', output_dir='aloro/split_by_category'):
    """
    Разделяет сплавы по категориям и сохраняет в отдельные JSON файлы
    """

    # Создаем директорию для выходных файлов
    os.makedirs(output_dir, exist_ok=True)

    # Загружаем данные
    print(f"Загрузка данных из {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Загружено {len(data)} записей")

    # Создаем маппинг категорий
    mapping = create_category_mapping()

    # Контейнеры для разделения
    categories = {
        'nickel_alloy': [],
        'titanium_alloy': [],
        'aluminum_alloy': [],
        'steel_alloy': [],
        'copper_alloy': [],
        'other': []
    }

    # Статистика по исходным категориям
    stats = defaultdict(lambda: {'total': 0, 'mapped_to': None, 'examples': []})

    # Разделяем записи
    for entry in data:
        original_cat = entry.get('category', 'unknown')
        stats[original_cat]['total'] += 1
        stats[original_cat]['examples'].append(entry.get('url', 'unknown')[:50])

        # Определяем целевую категорию
        target_cat = mapping.get(original_cat, 'other')
        stats[original_cat]['mapped_to'] = target_cat

        # Добавляем запись в соответствующий список
        categories[target_cat].append(entry)

    # Сохраняем результаты
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ РАЗДЕЛЕНИЯ")
    print("=" * 60)

    for cat, items in categories.items():
        output_file = os.path.join(output_dir, f'{cat}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

        count = len(items)
        percent = count / len(data) * 100
        print(f"\n{cat}.json")
        print(f"   Записей: {count} ({percent:.1f}%)")
        print(f"   Сохранено: {output_file}")

    # Сохраняем статистику маппинга
    stats_file = os.path.join(output_dir, 'mapping_statistics.json')

    # Форматируем статистику для сохранения
    stats_for_save = {}
    for cat, info in stats.items():
        stats_for_save[cat] = {
            'total': info['total'],
            'mapped_to': info['mapped_to'],
            'examples': info['examples'][:3]  # только 3 примера
        }

    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats_for_save, f, ensure_ascii=False, indent=2)

    print(f"\nСтатистика маппинга сохранена: {stats_file}")

    # Сохраняем также в CSV для удобства
    csv_file = os.path.join(output_dir, 'mapping_statistics.csv')
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write("original_category,target_category,count\n")
        for cat, info in sorted(stats.items(), key=lambda x: -x[1]['total']):
            f.write(f'"{cat}",{info["mapped_to"]},{info["total"]}\n')

    print(f"CSV статистика сохранена: {csv_file}")

    # Выводим детальную информацию о маппинге
    print("\n" + "-" * 60)
    print("ДЕТАЛИ МАППИНГА:")
    print("-" * 60)

    for cat, info in sorted(stats.items(), key=lambda x: -x[1]['total']):
        if info['total'] > 0:
            print(f"  {cat:45s} -> {info['mapped_to']:15s} ({info['total']} зап.)")

    return categories, stats


def create_summary_report(categories, output_dir='aloro/split_by_category'):
    """Создает сводный отчет о распределении"""

    report_file = os.path.join(output_dir, 'summary_report.txt')

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("ОТЧЕТ О РАЗДЕЛЕНИИ СПЛАВОВ ПО КАТЕГОРИЯМ\n")
        f.write("=" * 80 + "\n\n")

        total = 0
        for cat, items in categories.items():
            count = len(items)
            total += count
            f.write(f"\n{cat.upper()}\n")
            f.write(f"   Количество: {count}\n")
            f.write(f"   Файл: {cat}.json\n")

            # Добавляем примеры составов
            if items:
                f.write(f"\n   Примеры составов:\n")
                for i, item in enumerate(items[:3]):
                    comp = item.get('composition', {})
                    comp_str = ', '.join([f"{k}: {v}" for k, v in list(comp.items())[:5]])
                    f.write(f"     {i + 1}. {comp_str}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write(f"ВСЕГО ЗАПИСЕЙ: {total}\n")
        f.write("=" * 80 + "\n")

    print(f"\nСводный отчет сохранен: {report_file}")


def verify_mapping_coverage(mapping, stats):
    """Проверяет полноту маппинга"""

    all_categories = set(stats.keys())
    mapped_categories = set(mapping.keys())

    missing = all_categories - mapped_categories
    extra = mapped_categories - all_categories

    print("\n" + "=" * 60)
    print("ПРОВЕРКА ПОЛНОТЫ МАППИНГА")
    print("=" * 60)

    if missing:
        print(f"\nКатегории без маппинга ({len(missing)}):")
        for cat in sorted(missing):
            print(f"   - {cat}")
    else:
        print("\nВсе категории имеют маппинг!")

    if extra:
        print(f"\nЛишние категории в маппинге ({len(extra)}):")
        for cat in sorted(extra):
            print(f"   - {cat}")

    return missing, extra


if __name__ == "__main__":
    print("=" * 60)
    print("РАЗДЕЛЕНИЕ СПЛАВОВ ПО КАТЕГОРИЯМ")
    print("=" * 60)

    # 1. Разделяем сплавы
    categories, stats = split_alloys_by_category()

    # 2. Проверяем полноту маппинга
    mapping = create_category_mapping()
    missing, extra = verify_mapping_coverage(mapping, stats)

    # 3. Создаем сводный отчет
    create_summary_report(categories)

    print("\n" + "=" * 60)
    print("ГОТОВО!")
    print("=" * 60)
    print("\nРезультаты сохранены в директории: aloro/split_by_category/")
    print("   - nickel_alloy.json    - никелевые сплавы")
    print("   - titanium_alloy.json  - титановые сплавы")
    print("   - aluminum_alloy.json  - алюминиевые сплавы")
    print("   - steel_alloy.json     - стали")
    print("   - copper_alloy.json    - медные сплавы")
    print("   - other.json           - остальные")
    print("   - mapping_statistics.json - статистика маппинга")
    print("   - mapping_statistics.csv  - статистика в CSV")
    print("   - summary_report.txt      - сводный отчет")