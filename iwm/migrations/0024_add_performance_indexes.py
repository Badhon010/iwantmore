from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iwm', '0023_order_order_number'),
    ]

    operations = [
        # Product.is_featured
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['is_featured'], name='iwm_product_is_feat_idx'),
        ),
        # Review.created_at
        migrations.AddIndex(
            model_name='review',
            index=models.Index(fields=['created_at'], name='iwm_review_created_idx'),
        ),
        # Review(product_id, created_at) — product detail page review listing
        migrations.AddIndex(
            model_name='review',
            index=models.Index(fields=['product', 'created_at'], name='iwm_review_product_date_idx'),
        ),
        # NewsletterSubscriber.is_active — bulk email filter
        migrations.AddIndex(
            model_name='newslettersubscriber',
            index=models.Index(fields=['is_active'], name='iwm_newsletter_active_idx'),
        ),
        # Coupon(is_active, valid_to) — coupon validation
        migrations.AddIndex(
            model_name='coupon',
            index=models.Index(fields=['is_active', 'valid_to'], name='iwm_coupon_active_validto_idx'),
        ),
    ]
