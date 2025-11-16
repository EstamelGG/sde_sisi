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

def get_type_name(type_id, types_data):
    """获取物品名称"""
    if type_id in types_data:
        type_data = types_data[type_id]
        name_data = type_data.get("name", {})
        # 优先使用中文名称，没有则使用英文
        return name_data.get("zh") or name_data.get("en", f"TypeID {type_id}")
    else:
        return f"TypeID {type_id}"

def load_blueprints_delta(delta_dir):
    """加载 blueprints.delta.jsonl 文件，提取新增、移除、改动的蓝图"""
    added_blueprints = {}
    removed_blueprints = {}
    changed_blueprints = {}
    
    blueprints_delta_file = f"{delta_dir}/blueprints.delta.jsonl"
    if os.path.exists(blueprints_delta_file):
        print(f"处理 blueprints delta 文件: {blueprints_delta_file}")
        with open(blueprints_delta_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    action = record.get("action")
                    blueprint_id = record.get("id")
                    blueprint_data = record.get("data", {})
                    
                    if action == "added":
                        added_blueprints[blueprint_id] = blueprint_data
                    elif action == "removed":
                        removed_blueprints[blueprint_id] = blueprint_data
                    elif action == "changed":
                        changed_blueprints[blueprint_id] = blueprint_data
    else:
        print(f"未找到 blueprints delta 文件: {blueprints_delta_file}")
    
    return added_blueprints, removed_blueprints, changed_blueprints

def load_typedogma_delta(delta_dir):
    """加载 typeDogma.delta.jsonl 文件，提取改动的物品（changed）和新增的物品（added）"""
    changed_typedogma = {}
    added_typedogma = {}
    
    typedogma_delta_file = f"{delta_dir}/typeDogma.delta.jsonl"
    if os.path.exists(typedogma_delta_file):
        print(f"处理 typeDogma delta 文件: {typedogma_delta_file}")
        with open(typedogma_delta_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    action = record.get("action")
                    type_id = record.get("id")
                    typedogma_data = record.get("data", {})
                    
                    if action == "changed":
                        changed_typedogma[type_id] = typedogma_data
                    elif action == "added":
                        added_typedogma[type_id] = typedogma_data
    else:
        print(f"未找到 typeDogma delta 文件: {typedogma_delta_file}")
    
    return changed_typedogma, added_typedogma

def get_attribute_name(attribute_id, dogma_attributes_data):
    """获取属性名称，优先级：displayNameID.zh > displayNameID.en > name"""
    if attribute_id not in dogma_attributes_data:
        return f"AttributeID {attribute_id}"
    
    attr_data = dogma_attributes_data[attribute_id]
    display_name_id = attr_data.get("displayNameID", {})
    
    # 优先使用中文
    if "zh" in display_name_id:
        return display_name_id["zh"]
    # 其次使用英文
    if "en" in display_name_id:
        return display_name_id["en"]
    # 最后使用 name 字段
    if "name" in attr_data:
        return attr_data["name"]
    
    return f"AttributeID {attribute_id}"

def get_type_category_id(type_id, types_data, groups_data):
    """获取物品的 categoryID"""
    if type_id not in types_data:
        return None
    
    type_data = types_data[type_id]
    group_id = type_data.get("groupID")
    
    if group_id is None:
        return None
    
    if group_id not in groups_data:
        return None
    
    group_data = groups_data[group_id]
    return group_data.get("categoryID")

def compare_typedogma_attributes(old_typedogma, new_typedogma, dogma_attributes_data):
    """比对 typeDogma 中 dogmaAttributes 的变化"""
    changes = []
    
    # 将属性列表转换为字典，方便比对
    old_attrs = {attr.get("attributeID"): attr.get("value", 0) for attr in old_typedogma.get("dogmaAttributes", [])}
    new_attrs = {attr.get("attributeID"): attr.get("value", 0) for attr in new_typedogma.get("dogmaAttributes", [])}
    
    # 获取所有属性ID
    all_attr_ids = set(old_attrs.keys()) | set(new_attrs.keys())
    
    for attr_id in all_attr_ids:
        # 检查属性是否在 TQ 中存在（不仅仅是值是否为 0）
        is_new_attribute = attr_id not in old_attrs
        old_value = old_attrs.get(attr_id, 0)
        new_value = new_attrs.get(attr_id, 0)
        
        # 只关注有变化的属性
        if old_value != new_value:
            attr_name = get_attribute_name(attr_id, dogma_attributes_data)
            changes.append({
                "attributeID": attr_id,
                "attributeName": attr_name,
                "oldValue": old_value,
                "newValue": new_value,
                "isNewAttribute": is_new_attribute  # 标记是否为新增的属性类型
            })
    
    return changes

def analyze_type_attributes_changes(changed_typedogma, tq_typedogma_data, types_data, groups_data, 
                                    dogma_attributes_data, target_categories):
    """分析物品属性变化，只关注指定类别的物品"""
    items_with_changes = {}
    
    for type_id, new_typedogma in changed_typedogma.items():
        # 检查物品的 categoryID
        category_id = get_type_category_id(type_id, types_data, groups_data)
        
        # 只关注指定类别的物品
        if category_id not in target_categories:
            continue
        
        # 获取旧数据
        old_typedogma = tq_typedogma_data.get(type_id, {})
        
        # 比对属性变化
        changes = compare_typedogma_attributes(old_typedogma, new_typedogma, dogma_attributes_data)
        
        if changes:
            items_with_changes[type_id] = {
                "type_id": type_id,
                "changes": changes
            }
    
    return items_with_changes

def create_attribute_changes_markdown(items_with_changes, types_data):
    """创建属性变化比对的 Markdown 内容"""
    lines = []
    
    lines.append("# 物品属性变更\n\n")
    
    if not items_with_changes:
        lines.append("本次更新未发现物品属性变更。\n\n")
    else:
        for type_id, item_info in sorted(items_with_changes.items()):
            # 获取物品名称
            item_name = get_type_name(type_id, types_data)
            lines.append(f"## {item_name}\n\n")
            
            # 列出所有属性变化
            for change in item_info["changes"]:
                attr_name = change["attributeName"]
                old_value = change["oldValue"]
                new_value = change["newValue"]
                is_new_attribute = change.get("isNewAttribute", False)
                
                # 格式化数值显示
                if isinstance(old_value, float) and old_value.is_integer():
                    old_value = int(old_value)
                if isinstance(new_value, float) and new_value.is_integer():
                    new_value = int(new_value)
                
                # 如果是新增的属性类型，显示更清晰
                if is_new_attribute:
                    lines.append(f"- {attr_name}: 新增属性 (值: {new_value})\n")
                else:
                    lines.append(f"- {attr_name}: {old_value} -> {new_value}\n")
            
            lines.append("\n")
    
    return "".join(lines)

def compare_activity_changes(old_activity, new_activity, types_data):
    """比对活动（manufacturing 或 reaction）的变化"""
    changes = {
        "materials": [],
        "products": []
    }
    
    # 比对材料变化
    old_materials = {m.get("typeID"): m.get("quantity", 0) for m in old_activity.get("materials", [])}
    new_materials = {m.get("typeID"): m.get("quantity", 0) for m in new_activity.get("materials", [])}
    
    all_material_ids = set(old_materials.keys()) | set(new_materials.keys())
    for material_id in all_material_ids:
        old_qty = old_materials.get(material_id, 0)
        new_qty = new_materials.get(material_id, 0)
        
        if old_qty != new_qty:
            material_name = get_type_name(material_id, types_data)
            # 统一使用 "旧值 -> 新值" 格式，更清晰直观
            changes["materials"].append({
                "name": material_name,
                "change": f"{old_qty} -> {new_qty}",
                "oldValue": old_qty,
                "newValue": new_qty
            })
    
    # 比对产品变化
    old_products = {p.get("typeID"): p.get("quantity", 0) for p in old_activity.get("products", [])}
    new_products = {p.get("typeID"): p.get("quantity", 0) for p in new_activity.get("products", [])}
    
    all_product_ids = set(old_products.keys()) | set(new_products.keys())
    for product_id in all_product_ids:
        old_qty = old_products.get(product_id, 0)
        new_qty = new_products.get(product_id, 0)
        
        if old_qty != new_qty:
            product_name = get_type_name(product_id, types_data)
            # 统一使用 "旧值 -> 新值" 格式，更清晰直观
            changes["products"].append({
                "name": product_name,
                "change": f"{old_qty} -> {new_qty}",
                "oldValue": old_qty,
                "newValue": new_qty
            })
    
    return changes

def analyze_blueprint_changes(blueprint_id, old_blueprint, new_blueprint, types_data):
    """分析单个蓝图的变化"""
    changes = {
        "manufacturing": {
            "materials": [],
            "products": []
        },
        "reaction": {
            "materials": [],
            "products": []
        }
    }
    
    old_activities = old_blueprint.get("activities", {})
    new_activities = new_blueprint.get("activities", {})
    
    # 比对 manufacturing 活动
    old_manufacturing = old_activities.get("manufacturing", {})
    new_manufacturing = new_activities.get("manufacturing", {})
    
    if old_manufacturing or new_manufacturing:
        manufacturing_changes = compare_activity_changes(old_manufacturing, new_manufacturing, types_data)
        changes["manufacturing"]["materials"] = manufacturing_changes["materials"]
        changes["manufacturing"]["products"] = manufacturing_changes["products"]
    
    # 比对 reaction 活动
    old_reaction = old_activities.get("reaction", {})
    new_reaction = new_activities.get("reaction", {})
    
    if old_reaction or new_reaction:
        reaction_changes = compare_activity_changes(old_reaction, new_reaction, types_data)
        changes["reaction"]["materials"] = reaction_changes["materials"]
        changes["reaction"]["products"] = reaction_changes["products"]
    
    return changes

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

def create_blueprint_comparison_markdown(added_blueprints, removed_blueprints, changed_blueprints, 
                                         tq_blueprints_data, sisi_blueprints_data, types_data):
    """创建蓝图比对的 Markdown 内容"""
    lines = []
    
    lines.append("# 蓝图变更\n\n")
    
    # 新增蓝图
    if added_blueprints:
        lines.append("## 新增蓝图\n\n")
        for blueprint_id, blueprint_data in sorted(added_blueprints.items()):
            # 获取蓝图名称（通过 blueprintTypeID）
            blueprint_type_id = blueprint_data.get("blueprintTypeID", blueprint_id)
            blueprint_name = get_type_name(blueprint_type_id, types_data)
            lines.append(f"### {blueprint_name} (Blueprint ID: {blueprint_id})\n\n")
            
            # 获取 activities 信息
            activities = blueprint_data.get("activities", {})
            
            # 显示 manufacturing 活动
            manufacturing = activities.get("manufacturing", {})
            if manufacturing:
                lines.append("**制造活动 (Manufacturing):**\n")
                # 材料
                materials = manufacturing.get("materials", [])
                if materials:
                    lines.append("  - 材料:\n")
                    for material in materials:
                        material_name = get_type_name(material.get("typeID"), types_data)
                        quantity = material.get("quantity", 0)
                        lines.append(f"    - {material_name} × {quantity}\n")
                
                # 产品
                products = manufacturing.get("products", [])
                if products:
                    lines.append("  - 输出物品:\n")
                    for product in products:
                        product_name = get_type_name(product.get("typeID"), types_data)
                        quantity = product.get("quantity", 0)
                        lines.append(f"    - {product_name} × {quantity}\n")
                lines.append("\n")
            
            # 显示 reaction 活动
            reaction = activities.get("reaction", {})
            if reaction:
                lines.append("**反应活动 (Reaction):**\n")
                # 材料
                materials = reaction.get("materials", [])
                if materials:
                    lines.append("  - 材料:\n")
                    for material in materials:
                        material_name = get_type_name(material.get("typeID"), types_data)
                        quantity = material.get("quantity", 0)
                        lines.append(f"    - {material_name} × {quantity}\n")
                
                # 产品
                products = reaction.get("products", [])
                if products:
                    lines.append("  - 输出物品:\n")
                    for product in products:
                        product_name = get_type_name(product.get("typeID"), types_data)
                        quantity = product.get("quantity", 0)
                        lines.append(f"    - {product_name} × {quantity}\n")
                lines.append("\n")
    else:
        lines.append("## 新增蓝图\n\n")
        lines.append("本次更新未发现新增蓝图。\n\n")
    
    # 改动蓝图
    if changed_blueprints:
        lines.append("## 蓝图变更\n\n")
        if not tq_blueprints_data:
            lines.append("⚠️ 警告: 未找到 TQ 蓝图数据，无法进行详细的变更比对。\n\n")
        
        for blueprint_id, new_blueprint_data in sorted(changed_blueprints.items()):
            # 获取旧蓝图数据
            old_blueprint_data = tq_blueprints_data.get(blueprint_id, {}) if tq_blueprints_data else {}
            
            blueprint_type_id = new_blueprint_data.get("blueprintTypeID", blueprint_id)
            blueprint_name = get_type_name(blueprint_type_id, types_data)
            lines.append(f"### {blueprint_name} (Blueprint ID: {blueprint_id})\n\n")
            
            if tq_blueprints_data:
                # 分析变化
                changes = analyze_blueprint_changes(blueprint_id, old_blueprint_data, new_blueprint_data, types_data)
                
                has_changes = False
                
                # 制造活动 (Manufacturing) 变化
                manufacturing_changes = changes.get("manufacturing", {})
                if manufacturing_changes.get("materials") or manufacturing_changes.get("products"):
                    has_changes = True
                    lines.append("**制造活动 (Manufacturing) 变更:**\n")
                    
                    # 材料变化
                    if manufacturing_changes["materials"]:
                        lines.append("  - 材料变更:\n")
                        for material_change in manufacturing_changes["materials"]:
                            lines.append(f"    - {material_change['name']}: {material_change['change']}\n")
                    
                    # 产品变化
                    if manufacturing_changes["products"]:
                        lines.append("  - 输出物品变更:\n")
                        for product_change in manufacturing_changes["products"]:
                            lines.append(f"    - {product_change['name']}: {product_change['change']}\n")
                    
                    lines.append("\n")
                
                # 反应活动 (Reaction) 变化
                reaction_changes = changes.get("reaction", {})
                if reaction_changes.get("materials") or reaction_changes.get("products"):
                    has_changes = True
                    lines.append("**反应活动 (Reaction) 变更:**\n")
                    
                    # 材料变化
                    if reaction_changes["materials"]:
                        lines.append("  - 材料变更:\n")
                        for material_change in reaction_changes["materials"]:
                            lines.append(f"    - {material_change['name']}: {material_change['change']}\n")
                    
                    # 产品变化
                    if reaction_changes["products"]:
                        lines.append("  - 输出物品变更:\n")
                        for product_change in reaction_changes["products"]:
                            lines.append(f"    - {product_change['name']}: {product_change['change']}\n")
                    
                    lines.append("\n")
                
                # 如果没有材料或产品变化，但蓝图确实改变了，说明可能是其他字段变化
                if not has_changes:
                    lines.append("蓝图配置已变更（非制造/反应活动变化）\n\n")
            else:
                # 没有 TQ 数据时，只显示 SISI 的当前配置
                activities = new_blueprint_data.get("activities", {})
                
                # 显示 manufacturing 活动
                manufacturing = activities.get("manufacturing", {})
                if manufacturing:
                    lines.append("**制造活动 (Manufacturing):**\n")
                    materials = manufacturing.get("materials", [])
                    if materials:
                        lines.append("  - 材料:\n")
                        for material in materials:
                            material_name = get_type_name(material.get("typeID"), types_data)
                            quantity = material.get("quantity", 0)
                            lines.append(f"    - {material_name} × {quantity}\n")
                    
                    products = manufacturing.get("products", [])
                    if products:
                        lines.append("  - 输出物品:\n")
                        for product in products:
                            product_name = get_type_name(product.get("typeID"), types_data)
                            quantity = product.get("quantity", 0)
                            lines.append(f"    - {product_name} × {quantity}\n")
                    lines.append("\n")
                
                # 显示 reaction 活动
                reaction = activities.get("reaction", {})
                if reaction:
                    lines.append("**反应活动 (Reaction):**\n")
                    materials = reaction.get("materials", [])
                    if materials:
                        lines.append("  - 材料:\n")
                        for material in materials:
                            material_name = get_type_name(material.get("typeID"), types_data)
                            quantity = material.get("quantity", 0)
                            lines.append(f"    - {material_name} × {quantity}\n")
                    
                    products = reaction.get("products", [])
                    if products:
                        lines.append("  - 输出物品:\n")
                        for product in products:
                            product_name = get_type_name(product.get("typeID"), types_data)
                            quantity = product.get("quantity", 0)
                            lines.append(f"    - {product_name} × {quantity}\n")
                    lines.append("\n")
    else:
        lines.append("## 蓝图变更\n\n")
        lines.append("本次更新未发现蓝图变更。\n\n")
    
    return "".join(lines)

def analyze_new_items(added_types, groups_data, categories_data, added_typedogma, 
                     typedogma_data, dogma_attributes_data, target_categories):
    """分析所有新增物品，获取类别和组别信息，对指定类别的物品收集属性信息"""
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
        category_id = None
        
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
        
        item_info = {
            "name": item_name,
            "description": item_description,
            "type_id": type_id,
            "group_id": group_id,
            "category_id": category_id,
            "group_name": group_name,
            "category_name": category_name
        }
        
        # 只对指定类别的物品收集属性信息
        if category_id in target_categories:
            # 优先从 added_typedogma 获取，如果没有则从完整的 typedogma_data 获取
            item_typedogma = added_typedogma.get(type_id)
            if item_typedogma is None and typedogma_data:
                item_typedogma = typedogma_data.get(type_id, {})
            
            if item_typedogma:
                attributes = []
                dogma_attributes = item_typedogma.get("dogmaAttributes", [])
                
                for attr in dogma_attributes:
                    attribute_id = attr.get("attributeID")
                    attribute_value = attr.get("value", 0)
                    
                    # 跳过值为 0 的属性（通常表示未设置）
                    if attribute_value == 0:
                        continue
                    
                    # 获取属性名称
                    attribute_name = get_attribute_name(attribute_id, dogma_attributes_data)
                    
                    # 格式化数值显示
                    if isinstance(attribute_value, float) and attribute_value.is_integer():
                        attribute_value = int(attribute_value)
                    
                    attributes.append({
                        "attributeID": attribute_id,
                        "attributeName": attribute_name,
                        "value": attribute_value
                    })
                
                # 按属性名称排序
                attributes.sort(key=lambda x: x["attributeName"])
                item_info["attributes"] = attributes
            else:
                item_info["attributes"] = []
        else:
            # 非目标类别，不收集属性
            item_info["attributes"] = None
        
        new_items.append(item_info)
    
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
    
    # TQ 数据文件（可选，用于蓝图比对）
    tq_blueprints_file = "tq-jsonl/blueprints.jsonl"
    
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
    
    # 加载 TQ blueprints 数据（用于蓝图比对）
    tq_blueprints_data = {}
    if os.path.exists(tq_blueprints_file):
        print("加载 TQ blueprints 数据...")
        tq_blueprints_data = load_jsonl(tq_blueprints_file)
        print(f"加载了 {len(tq_blueprints_data)} 个 TQ blueprints")
    else:
        print(f"警告: 未找到 TQ blueprints 文件 {tq_blueprints_file}，蓝图比对功能可能受限")
    
    # 加载 dogmaAttributes 数据（用于属性名称映射）
    print("加载 SISI dogmaAttributes 数据...")
    sisi_dogma_attributes_data = load_jsonl("sisi-jsonl/dogmaAttributes.jsonl")
    print(f"加载了 {len(sisi_dogma_attributes_data)} 个 SISI dogmaAttributes")
    
    # 加载 TQ typeDogma 数据（用于属性比对）
    tq_typedogma_file = "tq-jsonl/typeDogma.jsonl"
    tq_typedogma_data = {}
    if os.path.exists(tq_typedogma_file):
        print("加载 TQ typeDogma 数据...")
        tq_typedogma_data = load_jsonl(tq_typedogma_file)
        print(f"加载了 {len(tq_typedogma_data)} 个 TQ typeDogma")
    else:
        print(f"警告: 未找到 TQ typeDogma 文件 {tq_typedogma_file}，属性比对功能可能受限")
    
    # 加载 types delta 文件
    print("加载 types delta 文件...")
    added_types = load_delta_files("delta")
    print(f"找到 {len(added_types)} 个新增的 types")
    
    # 加载 blueprints delta 文件
    print("加载 blueprints delta 文件...")
    added_blueprints, removed_blueprints, changed_blueprints = load_blueprints_delta("delta")
    print(f"找到 {len(added_blueprints)} 个新增蓝图, {len(removed_blueprints)} 个移除蓝图, {len(changed_blueprints)} 个变更蓝图")
    
    # 加载 typeDogma delta 文件（关注 changed 和 added）
    print("加载 typeDogma delta 文件...")
    changed_typedogma, added_typedogma = load_typedogma_delta("delta")
    print(f"找到 {len(changed_typedogma)} 个属性变更的物品, {len(added_typedogma)} 个新增物品的属性")
    
    # 加载 SISI typeDogma 数据（用于获取新增物品的完整属性信息）
    sisi_typedogma_file = "sisi-jsonl/typeDogma.jsonl"
    sisi_typedogma_data = {}
    if os.path.exists(sisi_typedogma_file):
        print("加载 SISI typeDogma 数据...")
        sisi_typedogma_data = load_jsonl(sisi_typedogma_file)
        print(f"加载了 {len(sisi_typedogma_data)} 个 SISI typeDogma")
    else:
        print(f"警告: 未找到 SISI typeDogma 文件 {sisi_typedogma_file}，新增物品属性收集可能受限")
    
    # 分析物品属性变化（只关注指定类别的物品）
    target_categories = {4, 6, 7, 18, 20, 65, 66, 87}
    if changed_typedogma and tq_typedogma_data:
        print(f"分析类别 {target_categories} 的物品属性变化...")
        items_with_attribute_changes = analyze_type_attributes_changes(
            changed_typedogma, tq_typedogma_data, sisi_types_data, 
            sisi_groups_data, sisi_dogma_attributes_data, target_categories
        )
        print(f"找到 {len(items_with_attribute_changes)} 个有属性变化的物品")
    else:
        items_with_attribute_changes = {}
        if not tq_typedogma_data:
            print("警告: 未找到 TQ typeDogma 数据，无法进行属性比对")
    
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
    
    # 创建新增物品分析（包含属性信息）
    all_new_items = analyze_new_items(
        added_types, sisi_groups_data, sisi_categories_data,
        added_typedogma, sisi_typedogma_data, sisi_dogma_attributes_data, target_categories
    )
    
    # 创建 whats_new.md 文件
    with open("summary/whats_new.md", "w", encoding="utf-8") as f:
        f.write("# 新增物品\n\n")
        
        if not all_new_items:
            f.write("本次更新未发现新增物品。\n\n")
        else:
            # 按 categoryID 和 groupID 分组
            grouped_items = {}
            for item in all_new_items:
                category_id = item.get('category_id', 999)  # 未知类别排在最后
                group_id = item.get('group_id', 999)  # 未知组别排在最后
                
                if category_id not in grouped_items:
                    grouped_items[category_id] = {}
                if group_id not in grouped_items[category_id]:
                    grouped_items[category_id][group_id] = []
                
                grouped_items[category_id][group_id].append(item)
            
            # 按 categoryID 排序并输出
            for category_id in sorted(grouped_items.keys()):
                category_items = grouped_items[category_id]
                
                # 获取类别名称（从第一个物品中获取）
                first_item = next(iter(category_items.values()))[0]
                category_display_name = first_item.get('category_name', '未知类别')
                
                f.write(f"## {category_display_name}\n\n")
                
                # 按 groupID 排序并输出
                for group_id in sorted(category_items.keys()):
                    group_items = category_items[group_id]
                    
                    # 获取组别名称
                    group_display_name = group_items[0].get('group_name', '未知组别')
                    
                    f.write(f"### {group_display_name}\n\n")
                    
                    # 输出该组别的所有物品
                    for item in group_items:
                        description = item.get('description', '')
                        attributes = item.get('attributes')
                        
                        if description:
                            f.write(f"- **{item['name']}**\n")
                            f.write(f"  - {description}\n")
                        else:
                            f.write(f"- **{item['name']}**\n")
                        
                        # 如果是目标类别且有属性信息，显示属性
                        if attributes is not None and attributes:
                            f.write(f"  - 属性:\n")
                            for attr in attributes:
                                attr_name = attr.get('attributeName', f"AttributeID {attr.get('attributeID')}")
                                attr_value = attr.get('value', 0)
                                f.write(f"    - {attr_name}: {attr_value}\n")
                        
                        f.write("\n")
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
        
        # 添加蓝图比对部分
        f.write("\n")
        blueprint_comparison = create_blueprint_comparison_markdown(
            added_blueprints, removed_blueprints, changed_blueprints,
            tq_blueprints_data, sisi_blueprints_data, sisi_types_data
        )
        f.write(blueprint_comparison)
        
        # 添加物品属性变更部分
        f.write("\n")
        attribute_changes = create_attribute_changes_markdown(
            items_with_attribute_changes, sisi_types_data
        )
        f.write(attribute_changes)
    
    print(f"\n=== 汇总完成 ===")
    print(f"新增 Types 总数: {len(added_types)}")
    print(f"新增飞船数量: {len(new_ships)}")
    print(f"类别分布: {dict(category_stats)}")
    print(f"报告已保存到 summary/ 目录")

if __name__ == "__main__":
    main()
