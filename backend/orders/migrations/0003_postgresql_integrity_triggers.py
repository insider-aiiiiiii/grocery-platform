from django.db import migrations


def install_postgresql_triggers(apps, schema_editor):
    """Enforce cross-table tenant ownership and snapshot immutability in PostgreSQL."""
    if schema_editor.connection.vendor != "postgresql":
        return

    statements = [
        """
        CREATE FUNCTION orders_check_order_shop_customer() RETURNS trigger AS $$
        DECLARE customer_shop_id bigint;
        BEGIN
            SELECT shop_id INTO customer_shop_id FROM customers_customer
            WHERE id = NEW.customer_id FOR SHARE;
            IF customer_shop_id IS DISTINCT FROM NEW.shop_id THEN
                RAISE EXCEPTION 'Order customer must belong to the same Shop'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER orders_order_shop_customer_guard
        BEFORE INSERT OR UPDATE OF shop_id, customer_id ON orders_order
        FOR EACH ROW EXECUTE FUNCTION orders_check_order_shop_customer();
        """,
        """
        CREATE FUNCTION orders_check_item_shop_catalog() RETURNS trigger AS $$
        DECLARE order_shop_id bigint;
                product_shop_id bigint;
                variant_product_id bigint;
                variant_parent_shop_id bigint;
        BEGIN
            SELECT shop_id INTO order_shop_id FROM orders_order
            WHERE id = NEW.order_id FOR SHARE;
            IF order_shop_id IS NULL THEN
                RAISE EXCEPTION 'Order item must reference an existing Order'
                    USING ERRCODE = 'foreign_key_violation';
            END IF;
            IF NEW.product_id IS NOT NULL THEN
                SELECT shop_id INTO product_shop_id
                FROM catalog_shopproduct WHERE id = NEW.product_id FOR SHARE;
                IF product_shop_id IS DISTINCT FROM order_shop_id THEN
                    RAISE EXCEPTION 'Order item product must belong to the Order Shop'
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            IF NEW.variant_id IS NOT NULL THEN
                SELECT product_id INTO variant_product_id
                FROM catalog_productvariant WHERE id = NEW.variant_id FOR SHARE;
                IF variant_product_id IS NOT NULL THEN
                    SELECT shop_id INTO variant_parent_shop_id FROM catalog_shopproduct
                    WHERE id = variant_product_id FOR SHARE;
                END IF;
                IF variant_product_id IS NULL OR variant_parent_shop_id IS DISTINCT FROM order_shop_id THEN
                    RAISE EXCEPTION 'Order item variant must belong to the Order Shop'
                        USING ERRCODE = 'check_violation';
                END IF;
                IF NEW.product_id IS NOT NULL AND NEW.product_id <> variant_product_id THEN
                    RAISE EXCEPTION 'Order item variant must belong to its referenced product'
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER orders_orderitem_shop_catalog_guard
        BEFORE INSERT OR UPDATE OF order_id, product_id, variant_id ON orders_orderitem
        FOR EACH ROW EXECUTE FUNCTION orders_check_item_shop_catalog();
        """,
        """
        CREATE FUNCTION orders_prevent_customer_shop_change() RETURNS trigger AS $$
        BEGIN
            IF NEW.shop_id IS DISTINCT FROM OLD.shop_id AND EXISTS (
                SELECT 1 FROM orders_order o
                WHERE o.customer_id = OLD.id AND o.shop_id <> NEW.shop_id
            ) THEN
                RAISE EXCEPTION 'Customer Shop cannot change while historical Orders reference it'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER orders_customer_shop_guard
        BEFORE UPDATE OF shop_id ON customers_customer
        FOR EACH ROW EXECUTE FUNCTION orders_prevent_customer_shop_change();
        """,
        """
        CREATE FUNCTION orders_prevent_product_shop_change() RETURNS trigger AS $$
        BEGIN
            IF NEW.shop_id IS DISTINCT FROM OLD.shop_id AND EXISTS (
                SELECT 1 FROM orders_orderitem i
                JOIN orders_order o ON o.id = i.order_id
                LEFT JOIN catalog_productvariant v ON v.id = i.variant_id
                WHERE (i.product_id = OLD.id OR v.product_id = OLD.id)
                  AND o.shop_id <> NEW.shop_id
            ) THEN
                RAISE EXCEPTION 'Catalog product Shop cannot change while referenced by historical Order Items'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER orders_product_shop_guard
        BEFORE UPDATE OF shop_id ON catalog_shopproduct
        FOR EACH ROW EXECUTE FUNCTION orders_prevent_product_shop_change();
        """,
        """
        CREATE FUNCTION orders_prevent_variant_product_change() RETURNS trigger AS $$
        BEGIN
            IF NEW.product_id IS DISTINCT FROM OLD.product_id AND EXISTS (
                SELECT 1 FROM orders_orderitem i
                JOIN orders_order o ON o.id = i.order_id
                JOIN catalog_shopproduct p ON p.id = NEW.product_id
                WHERE i.variant_id = OLD.id
                  AND (o.shop_id <> p.shop_id OR (i.product_id IS NOT NULL AND i.product_id <> NEW.product_id))
            ) THEN
                RAISE EXCEPTION 'Variant product cannot change across historical Order Shop boundaries'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER orders_variant_product_guard
        BEFORE UPDATE OF product_id ON catalog_productvariant
        FOR EACH ROW EXECUTE FUNCTION orders_prevent_variant_product_change();
        """,
        """
        CREATE FUNCTION orders_prevent_order_snapshot_change() RETURNS trigger AS $$
        BEGIN
            IF ROW(NEW.shop_id, NEW.customer_id, NEW.fulfillment_type,
                   NEW.customer_name_snapshot, NEW.customer_phone_snapshot,
                   NEW.delivery_fee_type_snapshot, NEW.delivery_charge_snapshot)
               IS DISTINCT FROM
               ROW(OLD.shop_id, OLD.customer_id, OLD.fulfillment_type,
                   OLD.customer_name_snapshot, OLD.customer_phone_snapshot,
                   OLD.delivery_fee_type_snapshot, OLD.delivery_charge_snapshot) THEN
                RAISE EXCEPTION 'Historical Order context and checkout snapshots are immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER orders_order_snapshot_immutable
        BEFORE UPDATE ON orders_order
        FOR EACH ROW EXECUTE FUNCTION orders_prevent_order_snapshot_change();
        """,
        """
        CREATE FUNCTION orders_prevent_item_snapshot_change() RETURNS trigger AS $$
        BEGIN
            IF ROW(NEW.order_id, NEW.product_name_snapshot, NEW.variant_name_snapshot,
                   NEW.sku_snapshot, NEW.unit_snapshot, NEW.attributes_snapshot,
                   NEW.ordered_quantity, NEW.unit_price_snapshot)
               IS DISTINCT FROM
               ROW(OLD.order_id, OLD.product_name_snapshot, OLD.variant_name_snapshot,
                   OLD.sku_snapshot, OLD.unit_snapshot, OLD.attributes_snapshot,
                   OLD.ordered_quantity, OLD.unit_price_snapshot) THEN
                RAISE EXCEPTION 'Historical Order Item snapshots are immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER orders_orderitem_snapshot_immutable
        BEFORE UPDATE ON orders_orderitem
        FOR EACH ROW EXECUTE FUNCTION orders_prevent_item_snapshot_change();
        """,
        """
        CREATE FUNCTION orders_prevent_address_snapshot_change() RETURNS trigger AS $$
        BEGIN
            IF ROW(NEW.order_id, NEW.recipient_name, NEW.recipient_phone, NEW.address_line,
                   NEW.area, NEW.city, NEW.state, NEW.pincode, NEW.landmark, NEW.delivery_notes)
               IS DISTINCT FROM
               ROW(OLD.order_id, OLD.recipient_name, OLD.recipient_phone, OLD.address_line,
                   OLD.area, OLD.city, OLD.state, OLD.pincode, OLD.landmark, OLD.delivery_notes) THEN
                RAISE EXCEPTION 'Historical delivery address snapshots are immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER orders_address_snapshot_immutable
        BEFORE UPDATE ON orders_orderdeliveryaddress
        FOR EACH ROW EXECUTE FUNCTION orders_prevent_address_snapshot_change();
        """,
        """
        CREATE FUNCTION orders_check_delivery_address_requirement() RETURNS trigger AS $$
        DECLARE order_ids bigint[];
                candidate_order_id bigint;
                fulfillment varchar(16);
        BEGIN
            IF TG_TABLE_NAME = 'orders_order' THEN
                order_ids := ARRAY[NEW.id];
            ELSIF TG_OP = 'DELETE' THEN
                order_ids := ARRAY[OLD.order_id];
            ELSIF TG_OP = 'UPDATE' AND OLD.order_id IS DISTINCT FROM NEW.order_id THEN
                order_ids := ARRAY[OLD.order_id, NEW.order_id];
            ELSE
                order_ids := ARRAY[NEW.order_id];
            END IF;

            FOREACH candidate_order_id IN ARRAY order_ids LOOP
                SELECT fulfillment_type INTO fulfillment
                FROM orders_order WHERE id = candidate_order_id;
                IF NOT FOUND THEN
                    CONTINUE;
                END IF;

                IF fulfillment = 'HOME_DELIVERY' AND NOT EXISTS (
                    SELECT 1 FROM orders_orderdeliveryaddress
                    WHERE order_id = candidate_order_id
                ) THEN
                    RAISE EXCEPTION 'Home Delivery Orders require a delivery address snapshot'
                        USING ERRCODE = 'check_violation';
                ELSIF fulfillment = 'PICKUP' AND EXISTS (
                    SELECT 1 FROM orders_orderdeliveryaddress
                    WHERE order_id = candidate_order_id
                ) THEN
                    RAISE EXCEPTION 'Pickup Orders cannot have a delivery address snapshot'
                        USING ERRCODE = 'check_violation';
                END IF;
            END LOOP;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        CREATE CONSTRAINT TRIGGER orders_order_delivery_address_required
        AFTER INSERT OR UPDATE ON orders_order
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION orders_check_delivery_address_requirement();
        CREATE CONSTRAINT TRIGGER orders_address_fulfillment_guard
        AFTER INSERT OR UPDATE OR DELETE ON orders_orderdeliveryaddress
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION orders_check_delivery_address_requirement();
        """,
    ]
    with schema_editor.connection.cursor() as cursor:
        for statement in statements:
            # psycopg 3 requires simple-query mode for a function plus trigger
            # definition in one migration statement; these static SQL blocks
            # contain no parameters and run only on PostgreSQL.
            cursor.cursor.execute(statement, prepare=False)


def remove_postgresql_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    statements = [
        ("orders_order", "orders_order_snapshot_immutable", "orders_prevent_order_snapshot_change"),
        ("orders_orderitem", "orders_orderitem_snapshot_immutable", "orders_prevent_item_snapshot_change"),
        ("orders_orderdeliveryaddress", "orders_address_snapshot_immutable", "orders_prevent_address_snapshot_change"),
        ("orders_order", "orders_order_delivery_address_required", "orders_check_delivery_address_requirement"),
        ("orders_orderdeliveryaddress", "orders_address_fulfillment_guard", "orders_check_delivery_address_requirement"),
        ("orders_order", "orders_order_shop_customer_guard", "orders_check_order_shop_customer"),
        ("orders_orderitem", "orders_orderitem_shop_catalog_guard", "orders_check_item_shop_catalog"),
        ("customers_customer", "orders_customer_shop_guard", "orders_prevent_customer_shop_change"),
        ("catalog_shopproduct", "orders_product_shop_guard", "orders_prevent_product_shop_change"),
        ("catalog_productvariant", "orders_variant_product_guard", "orders_prevent_variant_product_change"),
    ]
    with schema_editor.connection.cursor() as cursor:
        for table, trigger, _ in statements:
            cursor.execute(f'DROP TRIGGER IF EXISTS {trigger} ON {table}')
        for function in dict.fromkeys(function for _, _, function in statements):
            cursor.execute(f'DROP FUNCTION IF EXISTS {function}()')


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0008_catalog_constraints_and_indexes"),
        ("customers", "0002_customer_customers_customer_whatsapp_not_empty"),
        ("orders", "0002_order_orders_order_customer_name_required_and_more"),
    ]

    operations = [
        migrations.RunPython(install_postgresql_triggers, remove_postgresql_triggers),
    ]
