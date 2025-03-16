import os
import django
import sys

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iwantmore.settings')
django.setup()

from django.utils.text import slugify
from iwm.models import Product

def fix_product_slugs():
    """
    Ensure all products have a valid slug generated from their name.
    """
    print("Checking and fixing product slugs...")
    
    try:
        # Count total products
        total_products = Product.objects.count()
        if total_products == 0:
            print("No products found in the database.")
            return
            
        print(f"Found {total_products} products in the database.")
        
        # Get all products
        products = Product.objects.all()
        fixed_count = 0
        already_ok_count = 0
        
        for product in products:
            print(f"Product ID: {product.id}, Name: {product.name}, Current Slug: {repr(product.slug)}")
            
            # Generate slug if missing or empty
            if not product.slug:
                base_slug = slugify(product.name)
                if not base_slug:  # If name doesn't produce a valid slug
                    base_slug = f"product-{product.id}"
                    
                slug = base_slug
                
                # Ensure uniqueness by appending a number if needed
                counter = 1
                while Product.objects.filter(slug=slug).exclude(id=product.id).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                product.slug = slug
                product.save()
                print(f"  - UPDATED slug to: {product.slug}")
                fixed_count += 1
            else:
                print(f"  - Slug is OK")
                already_ok_count += 1
        
        print(f"\nSummary:")
        print(f"- Total products: {total_products}")
        print(f"- Products with good slugs: {already_ok_count}")
        print(f"- Products fixed: {fixed_count}")
        print("Done! All products now have valid slugs.")
        
    except Exception as e:
        print(f"Error: {e}")
        return

if __name__ == "__main__":
    fix_product_slugs() 