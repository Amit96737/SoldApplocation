from sqlalchemy import func
from shop import models
from typing import List, Union
from sqlalchemy.orm import Session


def size_exists(size_name: str, db: Session) -> bool:
    if not size_name:
        return False
    try:
        exists = db.query(models.Sizes).filter(func.lower(models.Sizes.size) == size_name.lower()).first() is not None
        return exists
    except Exception as e:
        print(f"Error checking size: {e}")
        return False


def brand_exists(brand_name: str, db: Session) -> bool:
    if not brand_name:
        return False
    try:
        exists = db.query(models.Brands).filter(func.lower(models.Brands.name) == brand_name.lower()).first() is not None
        return exists
    except Exception as e:
        print(f"Error checking brand: {e}")
        return False


def category_exists(category_name: str, db: Session) -> bool:
    if not category_name:
        return False
    try:
        exists = db.query(models.Category).filter(func.lower(models.Category.name) == category_name.lower()).first() is not None
        return exists
    except Exception as e:
        print(f"Error checking category: {e}")
        return False


def sub_category_exists(sub_cat_name: str, db: Session) -> bool:
    if not sub_cat_name:
        return False
    try:
        exists = db.query(models.SubCategory).filter(
            func.lower(models.SubCategory.name) == sub_cat_name.lower()
        ).first() is not None
        return exists
    except Exception as e:
        print(f"Error checking sub-category: {e}")
        return False


def colors_exist(color_list: List[str], db: Session) -> Union[bool, List[str]]:
    try:
        if not color_list:
            return True
        color_names_lower = [color.strip().lower() for color in color_list]
        db_colors = db.query(models.Colors.color_name).all()
        db_color_names = {color[0].strip().lower() for color in db_colors}
        invalid_colors = [color for color in color_names_lower if color not in db_color_names]

        return True if not invalid_colors else invalid_colors

    except Exception as e:
        print(f"Error colors: {e}")
        return False


def material_exist(material_list: List[str], db: Session) -> Union[bool, List[str]]:
    try:
        if not material_list:
            return True
        material_names_lower = [i.strip().lower() for i in material_list]
        db_materials = db.query(models.ItemMaterial.name).all()
        db_material_names = {i[0].strip().lower() for i in db_materials}
        invalid_materials = [i for i in material_names_lower if i not in db_material_names]

        return True if not invalid_materials else invalid_materials

    except Exception as e:
        print(f"Error materials: {e}")
        return False
