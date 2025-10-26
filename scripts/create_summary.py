#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汇总工具：分析新增的 types 并筛选出新的飞船
"""
import json
import os
import glob
import re
from collections import defaultdict

def load_jsonl(filename):
    """加载 JSONL 文件并返回字典"""
    data = {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    data[record["id"]] = record["data"]
    return data

def load_delta_files(delta_dir):
    """加载 types.delta.jsonl 文件，提取新增的 types"""
    added_types = {}
    
    types_delta_file = f"{delta_dir}/types.delta.jsonl"
    if os.path.exists(types_delta_file):
        print(f"处理 types delta 文件: {types_delta_file}")
        with open(types_delta_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    if record.get("action") == "added":
                        added_types[record["id"]] = record["data"]
    else:
        print(f"未找到 types delta 文件: {types_delta_file}")
    
    return added_types

def create_group_to_category_mapping(groups_data):
    """创建 groupID 到 categoryID 的映射表"""
    group_to_category = {}
    for group_id, group_data in groups_data.items():
        if "categoryID" in group_data:
            group_to_category[group_id] = group_data["categoryID"]
    return group_to_category

def analyze_new_types(added_types, groups_data, types_data):
    """分析新增的 types，找出属于飞船类别的"""
    print("创建 groupID 到 categoryID 的映射...")
    group_to_category = create_group_to_category_mapping(groups_data)
    
    # 统计 categoryID 分布
    category_stats = defaultdict(int)
    new_ships = {}
    
    print(f"分析 {len(added_types)} 个新增的 types...")
    
    for type_id, type_data in added_types.items():
        if "groupID" in type_data:
            group_id = type_data["groupID"]
            if group_id in group_to_category:
                category_id = group_to_category[group_id]
                category_stats[category_id] += 1
                
                # 如果是飞船类别 (categoryID == 6)
                if category_id == 6:
                    new_ships[type_id] = type_data
                    print(f"发现新飞船: TypeID {type_id}, GroupID {group_id}")
    
    return new_ships, category_stats

def create_summary_report(new_ships, category_stats):
    """创建汇总报告"""
    report = {
        "summary": {
            "total_new_types": len(new_ships),
            "category_distribution": dict(category_stats),
            "new_ships_count": len(new_ships)
        },
        "new_ships": new_ships
    }
    
    return report

def find_blueprints_for_ships(new_ships, sisi_blueprints_data, sisi_types_data):
    """为新飞船查找相关蓝图"""
    ship_blueprints = {}
    
    for ship_id, ship_data in new_ships.items():
        print(f"查找飞船 {ship_id} 的蓝图...")
        
        # 在蓝图中查找制造该飞船的蓝图
        blueprint_found = False
        for blueprint_id, blueprint_data in sisi_blueprints_data.items():
            if "activities" in blueprint_data and "manufacturing" in blueprint_data["activities"]:
                manufacturing = blueprint_data["activities"]["manufacturing"]
                if "products" in manufacturing:
                    for product in manufacturing["products"]:
                        if product.get("typeID") == ship_id:
                            # 找到制造该飞船的蓝图
                            blueprint_found = True
                            ship_blueprints[ship_id] = {
                                "blueprint_id": blueprint_id,
                                "blueprint_data": blueprint_data,
                                "materials": manufacturing.get("materials", [])
                            }
                            print(f"  找到蓝图: {blueprint_id}")
                            break
            if blueprint_found:
                break
        
        if not blueprint_found:
            ship_blueprints[ship_id] = {
                "blueprint_id": None,
                "blueprint_data": None,
                "materials": [],
                "status": "未找到蓝图"
            }
            print(f"  未找到蓝图")
    
    return ship_blueprints

def get_material_names(materials, types_data):
    """获取材料名称"""
    material_info = []
    
    for material in materials:
        type_id = material.get("typeID")
        quantity = material.get("quantity", 0)
        
        if type_id in types_data:
            type_data = types_data[type_id]
            name_data = type_data.get("name", {})
            
            # 优先使用中文名称，没有则使用英文
            name = name_data.get("zh") or name_data.get("en", f"TypeID {type_id}")
        else:
            name = f"TypeID {type_id}"
        
        material_info.append({
            "name": name,
            "quantity": quantity,
            "typeID": type_id
        })
    
    return material_info

def create_blueprint_analysis(new_ships, ship_blueprints, types_data):
    """创建蓝图分析报告"""
    analysis = []
    
    for ship_id, ship_data in new_ships.items():
        ship_name_data = ship_data.get("name", {})
        ship_name = ship_name_data.get("zh") or ship_name_data.get("en", f"TypeID {ship_id}")
        
        ship_info = {
            "ship_id": ship_id,
            "ship_name": ship_name,
            "blueprint_info": ship_blueprints.get(ship_id, {})
        }
        
        if ship_blueprints.get(ship_id, {}).get("status") == "未找到蓝图":
            ship_info["materials"] = []
            ship_info["status"] = "未找到蓝图"
        else:
            materials = ship_blueprints[ship_id].get("materials", [])
            ship_info["materials"] = get_material_names(materials, types_data)
            ship_info["status"] = "找到蓝图"
        
        analysis.append(ship_info)
    
    return analysis

def analyze_new_items(added_types, groups_data, categories_data):
    """分析所有新增物品，获取类别和组别信息"""
    new_items = []
    
    for type_id, type_data in added_types.items():
        # 获取物品名称
        name_data = type_data.get("name", {})
        item_name = name_data.get("zh") or name_data.get("en", f"TypeID {type_id}")
        
        # 获取物品描述
        description_data = type_data.get("description", {})
        raw_description = description_data.get("zh") or description_data.get("en", "")
        # 格式化描述：清除HTML标签、换行符和多余空白
        if raw_description:
            # 移除HTML标签
            clean_description = re.sub(r'<[^>]+>', '', raw_description)
            # 清除换行符和多余空白
            item_description = " ".join(clean_description.split())
        else:
            item_description = ""
        
        # 获取组别信息
        group_id = type_data.get("groupID")
        group_name = "未知组别"
        category_name = "未知类别"
        
        if group_id in groups_data:
            group_data = groups_data[group_id]
            group_name_data = group_data.get("name", {})
            group_name = group_name_data.get("zh") or group_name_data.get("en", f"GroupID {group_id}")
            
            # 获取类别信息
            category_id = group_data.get("categoryID")
            if category_id is not None and category_id in categories_data:
                category_data = categories_data[category_id]
                category_name_data = category_data.get("name", {})
                category_name = category_name_data.get("zh") or category_name_data.get("en", f"CategoryID {category_id}")
        
        new_items.append({
            "name": item_name,
            "description": item_description,
            "type_id": type_id,
            "group_name": group_name,
            "category_name": category_name
        })
    
    return new_items

def main():
    print("=== SDE 汇总工具 ===")
    
    # 检查必要的文件
    required_files = [
        "delta",
        "sisi-jsonl/groups.jsonl",
        "sisi-jsonl/types.jsonl",
        "sisi-jsonl/blueprints.jsonl",
        "sisi-jsonl/categories.jsonl"
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"错误: 找不到必要文件 {file_path}")
            return
    
    # 加载数据
    print("加载 SISI groups 数据...")
    sisi_groups_data = load_jsonl("sisi-jsonl/groups.jsonl")
    print(f"加载了 {len(sisi_groups_data)} 个 SISI groups")
    
    print("加载 SISI categories 数据...")
    sisi_categories_data = load_jsonl("sisi-jsonl/categories.jsonl")
    print(f"加载了 {len(sisi_categories_data)} 个 SISI categories")
    
    print("加载 SISI types 数据...")
    sisi_types_data = load_jsonl("sisi-jsonl/types.jsonl")
    print(f"加载了 {len(sisi_types_data)} 个 SISI types")
    
    print("加载 SISI blueprints 数据...")
    sisi_blueprints_data = load_jsonl("sisi-jsonl/blueprints.jsonl")
    print(f"加载了 {len(sisi_blueprints_data)} 个 SISI blueprints")
    
    # 加载 types delta 文件
    print("加载 types delta 文件...")
    added_types = load_delta_files("delta")
    print(f"找到 {len(added_types)} 个新增的 types")
    
    if not added_types:
        print("没有找到新增的 types，跳过分析")
        return
    
    # 分析新增的 types
    new_ships, category_stats = analyze_new_types(added_types, sisi_groups_data, sisi_types_data)
    
    # 查找新飞船的蓝图
    print("\n=== 蓝图分析 ===")
    ship_blueprints = find_blueprints_for_ships(new_ships, sisi_blueprints_data, sisi_types_data)
    
    # 创建蓝图分析
    blueprint_analysis = create_blueprint_analysis(new_ships, ship_blueprints, sisi_types_data)
    
    # 创建汇总报告
    report = create_summary_report(new_ships, category_stats)
    report["blueprint_analysis"] = blueprint_analysis
    
    # 保存新飞船数据
    os.makedirs("summary", exist_ok=True)
    with open("summary/new_ships.json", "w", encoding="utf-8") as f:
        json.dump(new_ships, f, ensure_ascii=False, indent=2)
    
    # 保存蓝图分析
    with open("summary/blueprint_analysis.json", "w", encoding="utf-8") as f:
        json.dump(blueprint_analysis, f, ensure_ascii=False, indent=2)
    
    # 保存完整报告
    with open("summary/summary_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 创建 Markdown 报告
    with open("summary/summary_report.md", "w", encoding="utf-8") as f:
        f.write("# SDE 变更汇总报告\n\n")
        f.write(f"## 新增 Types 统计\n")
        f.write(f"- 总新增 Types: {len(added_types)}\n")
        f.write(f"- 新增飞船数量: {len(new_ships)}\n\n")
        
        f.write("## 类别分布\n")
        for category_id, count in sorted(category_stats.items()):
            f.write(f"- CategoryID {category_id}: {count} 个\n")
        
        if new_ships:
            f.write("\n## 新增飞船列表\n")
            for type_id, type_data in new_ships.items():
                group_id = type_data.get("groupID", "未知")
                name = type_data.get("name", {}).get("en", f"TypeID {type_id}")
                f.write(f"- {name} (TypeID: {type_id}, GroupID: {group_id})\n")
        
        # 添加蓝图分析
        f.write("\n## 新飞船蓝图分析\n")
        for ship_info in blueprint_analysis:
            f.write(f"\n### {ship_info['ship_name']}\n")
            if ship_info['status'] == "未找到蓝图":
                f.write("- 未找到蓝图\n")
            else:
                f.write("制造材料:\n")
                for material in ship_info['materials']:
                    f.write(f"- {material['name']} ({material['quantity']} 数量)\n")
    
    # 创建简化的新飞船材料报告
    with open("summary/new_ships_materials.txt", "w", encoding="utf-8") as f:
        if not blueprint_analysis:
            f.write("本次更新未发现新飞船\n")
        else:
            for ship_info in blueprint_analysis:
                f.write(f"新增飞船：{ship_info['ship_name']}\n")
                if ship_info['status'] == "未找到蓝图":
                    f.write("- 未找到蓝图\n")
                else:
                    for material in ship_info['materials']:
                        f.write(f"- {material['name']}（{material['quantity']}数量）\n")
                f.write("\n")
    
    # 创建新增物品分析
    all_new_items = analyze_new_items(added_types, sisi_groups_data, sisi_categories_data)
    
    # 创建 whats_new.md 文件
    with open("summary/whats_new.md", "w", encoding="utf-8") as f:
        f.write("# 新增物品\n\n")
        
        if not all_new_items:
            f.write("本次更新未发现新增物品。\n\n")
        else:
            for item in all_new_items:
                category_name = item.get('category_name', '未知类别')
                group_name = item.get('group_name', '未知组别')
                description = item.get('description', '')
                if description:
                    f.write(f"- **{item['name']}**（{category_name}/{group_name}）\n")
                    f.write(f"  - {description}\n")
                else:
                    f.write(f"- {item['name']}（{category_name}/{group_name}）\n")
            f.write("\n")
        
        f.write("# 新增飞船\n\n")
        
        if not blueprint_analysis:
            f.write("本次更新未发现新飞船。\n")
        else:
            for ship_info in blueprint_analysis:
                f.write(f"## {ship_info['ship_name']}\n")
                
                if ship_info['status'] == "未找到蓝图":
                    f.write("- 未找到蓝图\n")
                else:
                    for material in ship_info['materials']:
                        f.write(f"- {material['name']} × {material['quantity']}\n")
                f.write("\n")
    
    print(f"\n=== 汇总完成 ===")
    print(f"新增 Types 总数: {len(added_types)}")
    print(f"新增飞船数量: {len(new_ships)}")
    print(f"类别分布: {dict(category_stats)}")
    print(f"报告已保存到 summary/ 目录")

if __name__ == "__main__":
    main()
