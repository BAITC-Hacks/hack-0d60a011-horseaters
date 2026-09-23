"""initial schema

Revision ID: 0001
Revises: None

Snapshot of the 24 existing ORM tables. No live application models are imported.
Enum columns use VARCHAR + CHECK, JSON uses JSONB on PostgreSQL, and partial
indexes retain their PostgreSQL and SQLite predicates. Python-side defaults
are intentionally not converted into server defaults.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Referenced tables precede dependent tables; self-FKs are created inline.
    op.create_table('categories',
    sa.Column('parent_id', sa.Uuid(), nullable=True),
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], name=op.f('fk_categories_parent_id_categories'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_categories')),
    sa.UniqueConstraint('code', name='uq_categories_code')
    )
    op.create_index('ix_categories_parent_id', 'categories', ['parent_id'], unique=False)
    op.create_table('suppliers',
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_suppliers')),
    sa.UniqueConstraint('code', name='uq_suppliers_code')
    )
    op.create_table('users',
    sa.Column('external_id', sa.String(length=255), nullable=False),
    sa.Column('display_name', sa.String(length=255), nullable=False),
    sa.Column('role', sa.Enum('buyer', 'admin', 'viewer', name='user_role', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('external_id', name='uq_users_external_id')
    )
    op.create_table('warehouses',
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_warehouses')),
    sa.UniqueConstraint('code', name='uq_warehouses_code')
    )
    op.create_table('calculation_runs',
    sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='calculation_run_status', native_enum=False, create_constraint=True, length=20), nullable=False),
    sa.Column('started_by', sa.Uuid(), nullable=False),
    sa.Column('warehouse_id', sa.Uuid(), nullable=True),
    sa.Column('category_id', sa.Uuid(), nullable=True),
    sa.Column('forecast_horizon_days', sa.Integer(), nullable=False),
    sa.Column('source_cutoff_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('algorithm_version', sa.String(length=100), nullable=False),
    sa.Column('parameters', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_details', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('forecast_horizon_days > 0', name=op.f('ck_calculation_runs_positive_forecast_horizon')),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_calculation_runs_category_id_categories'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['started_by'], ['users.id'], name=op.f('fk_calculation_runs_started_by_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name=op.f('fk_calculation_runs_warehouse_id_warehouses'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_calculation_runs'))
    )
    op.create_index(op.f('ix_calculation_runs_category_id'), 'calculation_runs', ['category_id'], unique=False)
    op.create_index(op.f('ix_calculation_runs_started_by'), 'calculation_runs', ['started_by'], unique=False)
    op.create_index('ix_calculation_runs_status_started_at', 'calculation_runs', ['status', 'started_at'], unique=False)
    op.create_index(op.f('ix_calculation_runs_warehouse_id'), 'calculation_runs', ['warehouse_id'], unique=False)
    op.create_table('import_batches',
    sa.Column('source_type', sa.Enum('sales', 'monthly_sales', 'inventory', 'stockout', 'in_transit', 'seasonality', 'supplier_terms', 'growth', 'material_requirements', name='import_source_type', native_enum=False, create_constraint=True, length=50), nullable=False),
    sa.Column('file_name', sa.String(length=500), nullable=False),
    sa.Column('file_checksum', sa.String(length=64), nullable=False),
    sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', name='import_status', native_enum=False, create_constraint=True, length=20), nullable=False),
    sa.Column('row_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('imported_by', sa.Uuid(), nullable=False),
    sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('error_details', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['imported_by'], ['users.id'], name=op.f('fk_import_batches_imported_by_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_import_batches'))
    )
    op.create_index('ix_import_batches_imported_by', 'import_batches', ['imported_by'], unique=False)
    op.create_index('uq_import_batches_completed_checksum', 'import_batches', ['file_checksum'], unique=True, postgresql_where=sa.text("status = 'completed'"), sqlite_where=sa.text("status = 'completed'"))
    op.create_table('products',
    sa.Column('sku', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=500), nullable=False),
    sa.Column('category_id', sa.Uuid(), nullable=True),
    sa.Column('unit', sa.String(length=32), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_products_category_id_categories'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_products')),
    sa.UniqueConstraint('sku', name='uq_products_sku')
    )
    op.create_index('ix_products_category_id', 'products', ['category_id'], unique=False)
    op.create_table('calculation_run_imports',
    sa.Column('calculation_run_id', sa.Uuid(), nullable=False),
    sa.Column('import_batch_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['calculation_run_id'], ['calculation_runs.id'], name=op.f('fk_calculation_run_imports_calculation_run_id_calculation_runs'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], name=op.f('fk_calculation_run_imports_import_batch_id_import_batches'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('calculation_run_id', 'import_batch_id', name=op.f('pk_calculation_run_imports'))
    )
    op.create_index(op.f('ix_calculation_run_imports_import_batch_id'), 'calculation_run_imports', ['import_batch_id'], unique=False)
    op.create_table('demand_forecasts',
    sa.Column('calculation_run_id', sa.Uuid(), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('warehouse_id', sa.Uuid(), nullable=False),
    sa.Column('forecast_period_start', sa.Date(), nullable=False),
    sa.Column('forecast_period_end', sa.Date(), nullable=False),
    sa.Column('raw_demand', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('return_adjustment', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('anomaly_adjustment', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('stockout_adjustment', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('cleaned_baseline', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('growth_rate', sa.Numeric(precision=12, scale=6), nullable=False),
    sa.Column('seasonality_index', sa.Numeric(precision=12, scale=6), nullable=False),
    sa.Column('forecast_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('details', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('forecast_period_end >= forecast_period_start', name=op.f('ck_demand_forecasts_valid_forecast_period')),
    sa.ForeignKeyConstraint(['calculation_run_id'], ['calculation_runs.id'], name=op.f('fk_demand_forecasts_calculation_run_id_calculation_runs'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_demand_forecasts_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name=op.f('fk_demand_forecasts_warehouse_id_warehouses'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_demand_forecasts')),
    sa.UniqueConstraint('calculation_run_id', 'product_id', 'warehouse_id', 'forecast_period_start', 'forecast_period_end', name='uq_demand_forecasts_run_product_warehouse_period')
    )
    op.create_index(op.f('ix_demand_forecasts_calculation_run_id'), 'demand_forecasts', ['calculation_run_id'], unique=False)
    op.create_index(op.f('ix_demand_forecasts_product_id'), 'demand_forecasts', ['product_id'], unique=False)
    op.create_index(op.f('ix_demand_forecasts_warehouse_id'), 'demand_forecasts', ['warehouse_id'], unique=False)
    op.create_table('growth_assumptions',
    sa.Column('import_batch_id', sa.Uuid(), nullable=True),
    sa.Column('product_id', sa.Uuid(), nullable=True),
    sa.Column('category_id', sa.Uuid(), nullable=True),
    sa.Column('warehouse_id', sa.Uuid(), nullable=True),
    sa.Column('growth_rate', sa.Numeric(precision=12, scale=6), nullable=False),
    sa.Column('valid_from', sa.Date(), nullable=False),
    sa.Column('valid_to', sa.Date(), nullable=True),
    sa.Column('source', sa.Enum('calculated', 'imported', 'manual', name='growth_source', native_enum=False, create_constraint=True, length=20), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('product_id IS NOT NULL OR category_id IS NOT NULL', name=op.f('ck_growth_assumptions_has_level')),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_growth_assumptions_category_id_categories'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], name=op.f('fk_growth_assumptions_import_batch_id_import_batches'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_growth_assumptions_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name=op.f('fk_growth_assumptions_warehouse_id_warehouses'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_growth_assumptions'))
    )
    op.create_index('ix_growth_assumptions_category_id', 'growth_assumptions', ['category_id'], unique=False)
    op.create_index('ix_growth_assumptions_import_batch_id', 'growth_assumptions', ['import_batch_id'], unique=False)
    op.create_index('ix_growth_assumptions_product_id', 'growth_assumptions', ['product_id'], unique=False)
    op.create_index('ix_growth_assumptions_warehouse_id', 'growth_assumptions', ['warehouse_id'], unique=False)
    op.create_table('in_transit_items',
    sa.Column('import_batch_id', sa.Uuid(), nullable=False),
    sa.Column('external_order_number', sa.String(length=255), nullable=True),
    sa.Column('supplier_id', sa.Uuid(), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('destination_warehouse_id', sa.Uuid(), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('expected_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.Enum('planned', 'in_transit', 'received', 'cancelled', name='transit_status', native_enum=False, create_constraint=True, length=20), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('quantity > 0', name=op.f('ck_in_transit_items_positive_quantity')),
    sa.ForeignKeyConstraint(['destination_warehouse_id'], ['warehouses.id'], name=op.f('fk_in_transit_items_destination_warehouse_id_warehouses'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], name=op.f('fk_in_transit_items_import_batch_id_import_batches'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_in_transit_items_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], name=op.f('fk_in_transit_items_supplier_id_suppliers'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_in_transit_items'))
    )
    op.create_index('ix_in_transit_items_destination_warehouse_id', 'in_transit_items', ['destination_warehouse_id'], unique=False)
    op.create_index('ix_in_transit_items_import_batch_id', 'in_transit_items', ['import_batch_id'], unique=False)
    op.create_index('ix_in_transit_items_product_warehouse_status_expected', 'in_transit_items', ['product_id', 'destination_warehouse_id', 'status', 'expected_at'], unique=False)
    op.create_index('ix_in_transit_items_supplier_id', 'in_transit_items', ['supplier_id'], unique=False)
    op.create_table('inventory_snapshots',
    sa.Column('import_batch_id', sa.Uuid(), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('warehouse_id', sa.Uuid(), nullable=False),
    sa.Column('snapshot_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('quantity_on_hand', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('quantity_reserved', sa.Numeric(precision=18, scale=4), server_default=sa.text('0'), nullable=False),
    sa.Column('quantity_available', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], name=op.f('fk_inventory_snapshots_import_batch_id_import_batches'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_inventory_snapshots_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name=op.f('fk_inventory_snapshots_warehouse_id_warehouses'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_inventory_snapshots')),
    sa.UniqueConstraint('import_batch_id', 'product_id', 'warehouse_id', 'snapshot_at', name='uq_inventory_snapshots_batch_product_warehouse_snapshot')
    )
    op.create_index('ix_inventory_snapshots_product_warehouse_snapshot', 'inventory_snapshots', ['product_id', 'warehouse_id', sa.literal_column('snapshot_at DESC')], unique=False)
    op.create_index('ix_inventory_snapshots_warehouse_id', 'inventory_snapshots', ['warehouse_id'], unique=False)
    op.create_table('material_requirements',
    sa.Column('import_batch_id', sa.Uuid(), nullable=False),
    sa.Column('external_document_number', sa.String(length=255), nullable=True),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('warehouse_id', sa.Uuid(), nullable=False),
    sa.Column('required_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('required_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.Enum('planned', 'fulfilled', 'cancelled', name='material_requirement_status', native_enum=False, create_constraint=True, length=20), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('required_quantity > 0', name=op.f('ck_material_requirements_positive_required_quantity')),
    sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], name=op.f('fk_material_requirements_import_batch_id_import_batches'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_material_requirements_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name=op.f('fk_material_requirements_warehouse_id_warehouses'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_material_requirements'))
    )
    op.create_index('ix_material_requirements_import_batch_id', 'material_requirements', ['import_batch_id'], unique=False)
    op.create_index('ix_material_requirements_product_id', 'material_requirements', ['product_id'], unique=False)
    op.create_index('ix_material_requirements_warehouse_id', 'material_requirements', ['warehouse_id'], unique=False)
    op.create_table('monthly_sales',
    sa.Column('import_batch_id', sa.Uuid(), nullable=False),
    sa.Column('source_row_number', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('warehouse_id', sa.Uuid(), nullable=True),
    sa.Column('period_start', sa.Date(), nullable=False),
    sa.Column('period_end', sa.Date(), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('period_end >= period_start', name=op.f('ck_monthly_sales_valid_period')),
    sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], name=op.f('fk_monthly_sales_import_batch_id_import_batches'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_monthly_sales_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name=op.f('fk_monthly_sales_warehouse_id_warehouses'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_monthly_sales')),
    sa.UniqueConstraint('import_batch_id', 'source_row_number', name='uq_monthly_sales_batch_row')
    )
    op.create_index('ix_monthly_sales_product_warehouse_period', 'monthly_sales', ['product_id', 'warehouse_id', 'period_start', 'period_end'], unique=False)
    op.create_index('ix_monthly_sales_warehouse_id', 'monthly_sales', ['warehouse_id'], unique=False)
    op.create_table('purchase_orders',
    sa.Column('order_number', sa.String(length=100), nullable=False),
    sa.Column('supplier_id', sa.Uuid(), nullable=False),
    sa.Column('warehouse_id', sa.Uuid(), nullable=False),
    sa.Column('created_from_run_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Enum('draft', 'approved', 'exported', 'cancelled', name='purchase_order_status', native_enum=False, create_constraint=True, length=20), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('approved_by', sa.Uuid(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('exported_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status NOT IN ('approved', 'exported') OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)", name=op.f('ck_purchase_orders_approved_order_has_audit')),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], name=op.f('fk_purchase_orders_approved_by_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_purchase_orders_created_by_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_from_run_id'], ['calculation_runs.id'], name=op.f('fk_purchase_orders_created_from_run_id_calculation_runs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], name=op.f('fk_purchase_orders_supplier_id_suppliers'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name=op.f('fk_purchase_orders_warehouse_id_warehouses'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_purchase_orders')),
    sa.UniqueConstraint('order_number', name=op.f('uq_purchase_orders_order_number'))
    )
    op.create_index(op.f('ix_purchase_orders_approved_by'), 'purchase_orders', ['approved_by'], unique=False)
    op.create_index(op.f('ix_purchase_orders_created_by'), 'purchase_orders', ['created_by'], unique=False)
    op.create_index(op.f('ix_purchase_orders_created_from_run_id'), 'purchase_orders', ['created_from_run_id'], unique=False)
    op.create_index('ix_purchase_orders_supplier_status_created', 'purchase_orders', ['supplier_id', 'status', 'created_at'], unique=False)
    op.create_index(op.f('ix_purchase_orders_warehouse_id'), 'purchase_orders', ['warehouse_id'], unique=False)
    op.create_table('recommendations',
    sa.Column('calculation_run_id', sa.Uuid(), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('warehouse_id', sa.Uuid(), nullable=False),
    sa.Column('supplier_id', sa.Uuid(), nullable=False),
    sa.Column('forecast_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('current_stock', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('in_transit_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('material_requirement_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('safety_stock', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('shortage_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('quantity_before_rounding', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('moq', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('package_size', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('recommended_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('effective_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('risk_score', sa.Numeric(precision=5, scale=4), nullable=False),
    sa.Column('urgency', sa.Enum('low', 'medium', 'high', 'critical', name='recommendation_urgency', native_enum=False, create_constraint=True, length=20), nullable=False),
    sa.Column('status', sa.Enum('suggested', 'adjusted', 'accepted', 'rejected', 'converted_to_order', name='recommendation_status', native_enum=False, create_constraint=True, length=30), nullable=False),
    sa.Column('explanation', sa.Text(), nullable=False),
    sa.Column('calculation_details', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('effective_quantity >= 0', name=op.f('ck_recommendations_nonnegative_effective_quantity')),
    sa.CheckConstraint('recommended_quantity >= 0', name=op.f('ck_recommendations_nonnegative_recommended_quantity')),
    sa.CheckConstraint('risk_score >= 0 AND risk_score <= 1', name=op.f('ck_recommendations_risk_score_range')),
    sa.CheckConstraint('version > 0', name=op.f('ck_recommendations_positive_version')),
    sa.ForeignKeyConstraint(['calculation_run_id'], ['calculation_runs.id'], name=op.f('fk_recommendations_calculation_run_id_calculation_runs'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_recommendations_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], name=op.f('fk_recommendations_supplier_id_suppliers'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name=op.f('fk_recommendations_warehouse_id_warehouses'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_recommendations')),
    sa.UniqueConstraint('calculation_run_id', 'product_id', 'warehouse_id', 'supplier_id', name='uq_recommendations_run_product_warehouse_supplier')
    )
    op.create_index('ix_recommendations_run_product_warehouse', 'recommendations', ['calculation_run_id', 'product_id', 'warehouse_id'], unique=False)
    op.create_index('ix_recommendations_run_supplier_urgency', 'recommendations', ['calculation_run_id', 'supplier_id', 'urgency'], unique=False)
    op.create_index('ix_recommendations_run_warehouse_status', 'recommendations', ['calculation_run_id', 'warehouse_id', 'status'], unique=False)
    op.create_table('sales_transactions',
    sa.Column('import_batch_id', sa.Uuid(), nullable=False),
    sa.Column('source_row_number', sa.Integer(), nullable=False),
    sa.Column('external_document_number', sa.String(length=255), nullable=True),
    sa.Column('sold_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('warehouse_id', sa.Uuid(), nullable=False),
    sa.Column('anonymous_customer_id', sa.String(length=255), nullable=True),
    sa.Column('transaction_type', sa.Enum('sale', 'return', name='transaction_type', native_enum=False, create_constraint=True, length=20), nullable=False),
    sa.Column('original_transaction_id', sa.Uuid(), nullable=True),
    sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('total_amount', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint("(transaction_type = 'sale' AND quantity > 0) OR (transaction_type = 'return' AND quantity < 0)", name=op.f('ck_sales_transactions_transaction_type_quantity_sign')),
    sa.CheckConstraint("original_transaction_id IS NULL OR transaction_type = 'return'", name=op.f('ck_sales_transactions_original_transaction_only_for_return')),
    sa.CheckConstraint('unit_price IS NULL OR unit_price >= 0', name=op.f('ck_sales_transactions_nonnegative_unit_price')),
    sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], name=op.f('fk_sales_transactions_import_batch_id_import_batches'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['original_transaction_id'], ['sales_transactions.id'], name=op.f('fk_sales_transactions_original_transaction_id_sales_transactions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_sales_transactions_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name=op.f('fk_sales_transactions_warehouse_id_warehouses'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sales_transactions')),
    sa.UniqueConstraint('import_batch_id', 'source_row_number', name='uq_sales_transactions_batch_row')
    )
    op.create_index('ix_sales_transactions_customer_sold', 'sales_transactions', ['anonymous_customer_id', 'sold_at'], unique=False, postgresql_where=sa.text('anonymous_customer_id IS NOT NULL'), sqlite_where=sa.text('anonymous_customer_id IS NOT NULL'))
    op.create_index('ix_sales_transactions_original_transaction_id', 'sales_transactions', ['original_transaction_id'], unique=False)
    op.create_index('ix_sales_transactions_product_warehouse_sold', 'sales_transactions', ['product_id', 'warehouse_id', 'sold_at'], unique=False)
    op.create_index('ix_sales_transactions_warehouse_id', 'sales_transactions', ['warehouse_id'], unique=False)
    op.create_table('seasonality_coefficients',
    sa.Column('import_batch_id', sa.Uuid(), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=True),
    sa.Column('category_id', sa.Uuid(), nullable=True),
    sa.Column('month', sa.SmallInteger(), nullable=False),
    sa.Column('coefficient', sa.Numeric(precision=12, scale=6), nullable=False),
    sa.Column('valid_from', sa.Date(), nullable=False),
    sa.Column('valid_to', sa.Date(), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('(product_id IS NOT NULL AND category_id IS NULL) OR (product_id IS NULL AND category_id IS NOT NULL)', name=op.f('ck_seasonality_coefficients_exactly_one_level')),
    sa.CheckConstraint('coefficient > 0', name=op.f('ck_seasonality_coefficients_positive_coefficient')),
    sa.CheckConstraint('month BETWEEN 1 AND 12', name=op.f('ck_seasonality_coefficients_month_range')),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_seasonality_coefficients_category_id_categories'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], name=op.f('fk_seasonality_coefficients_import_batch_id_import_batches'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_seasonality_coefficients_product_id_products'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_seasonality_coefficients'))
    )
    op.create_index('ix_seasonality_coefficients_category_id', 'seasonality_coefficients', ['category_id'], unique=False)
    op.create_index('ix_seasonality_coefficients_import_batch_id', 'seasonality_coefficients', ['import_batch_id'], unique=False)
    op.create_index('ix_seasonality_coefficients_product_id', 'seasonality_coefficients', ['product_id'], unique=False)
    op.create_table('stockout_periods',
    sa.Column('import_batch_id', sa.Uuid(), nullable=True),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('warehouse_id', sa.Uuid(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('source', sa.Enum('imported', 'inferred', 'manual', name='stockout_source', native_enum=False, create_constraint=True, length=20), nullable=False),
    sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('confidence IS NULL OR confidence BETWEEN 0 AND 1', name=op.f('ck_stockout_periods_confidence_range')),
    sa.CheckConstraint('ended_at IS NULL OR ended_at > started_at', name=op.f('ck_stockout_periods_valid_period')),
    sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], name=op.f('fk_stockout_periods_import_batch_id_import_batches'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_stockout_periods_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name=op.f('fk_stockout_periods_warehouse_id_warehouses'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_stockout_periods'))
    )
    op.create_index('ix_stockout_periods_import_batch_id', 'stockout_periods', ['import_batch_id'], unique=False)
    op.create_index('ix_stockout_periods_product_warehouse_period', 'stockout_periods', ['product_id', 'warehouse_id', 'started_at', 'ended_at'], unique=False)
    op.create_index('ix_stockout_periods_warehouse_id', 'stockout_periods', ['warehouse_id'], unique=False)
    op.create_table('supplier_products',
    sa.Column('supplier_id', sa.Uuid(), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('moq', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('package_size', sa.Numeric(precision=18, scale=4), server_default=sa.text('1'), nullable=False),
    sa.Column('lead_time_days', sa.Integer(), nullable=False),
    sa.Column('purchase_price', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('priority', sa.Integer(), server_default=sa.text('100'), nullable=False),
    sa.Column('is_primary', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('lead_time_days >= 0', name=op.f('ck_supplier_products_nonnegative_lead_time')),
    sa.CheckConstraint('moq > 0', name=op.f('ck_supplier_products_positive_moq')),
    sa.CheckConstraint('package_size > 0', name=op.f('ck_supplier_products_positive_package_size')),
    sa.CheckConstraint('purchase_price IS NULL OR purchase_price >= 0', name=op.f('ck_supplier_products_nonnegative_price')),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_supplier_products_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], name=op.f('fk_supplier_products_supplier_id_suppliers'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_supplier_products')),
    sa.UniqueConstraint('supplier_id', 'product_id', name='uq_supplier_products_supplier_product')
    )
    op.create_index('ix_supplier_products_product_id', 'supplier_products', ['product_id'], unique=False)
    op.create_index('uq_supplier_products_primary_product', 'supplier_products', ['product_id'], unique=True, postgresql_where=sa.text('is_active = true AND is_primary = true'), sqlite_where=sa.text('is_active = true AND is_primary = true'))
    op.create_table('detected_anomalies',
    sa.Column('calculation_run_id', sa.Uuid(), nullable=False),
    sa.Column('sales_transaction_id', sa.Uuid(), nullable=False),
    sa.Column('method', sa.String(length=50), nullable=False),
    sa.Column('original_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('replacement_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('threshold', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('details', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['calculation_run_id'], ['calculation_runs.id'], name=op.f('fk_detected_anomalies_calculation_run_id_calculation_runs'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sales_transaction_id'], ['sales_transactions.id'], name=op.f('fk_detected_anomalies_sales_transaction_id_sales_transactions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_detected_anomalies')),
    sa.UniqueConstraint('calculation_run_id', 'sales_transaction_id', 'method', name='uq_detected_anomalies_run_transaction_method')
    )
    op.create_index(op.f('ix_detected_anomalies_calculation_run_id'), 'detected_anomalies', ['calculation_run_id'], unique=False)
    op.create_index(op.f('ix_detected_anomalies_sales_transaction_id'), 'detected_anomalies', ['sales_transaction_id'], unique=False)
    op.create_table('order_exports',
    sa.Column('purchase_order_id', sa.Uuid(), nullable=False),
    sa.Column('format', sa.Enum('xlsx', 'csv', name='order_export_format', native_enum=False, create_constraint=True, length=20), nullable=False),
    sa.Column('file_name', sa.String(length=500), nullable=False),
    sa.Column('file_checksum', sa.String(length=64), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_order_exports_created_by_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], name=op.f('fk_order_exports_purchase_order_id_purchase_orders'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_order_exports'))
    )
    op.create_index(op.f('ix_order_exports_created_by'), 'order_exports', ['created_by'], unique=False)
    op.create_index(op.f('ix_order_exports_purchase_order_id'), 'order_exports', ['purchase_order_id'], unique=False)
    op.create_table('purchase_order_items',
    sa.Column('purchase_order_id', sa.Uuid(), nullable=False),
    sa.Column('recommendation_id', sa.Uuid(), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('recommended_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('approved_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('total_amount', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('approved_quantity > 0', name=op.f('ck_purchase_order_items_positive_approved_quantity')),
    sa.CheckConstraint('total_amount IS NULL OR total_amount >= 0', name=op.f('ck_purchase_order_items_nonnegative_total_amount')),
    sa.CheckConstraint('unit_price IS NULL OR unit_price >= 0', name=op.f('ck_purchase_order_items_nonnegative_unit_price')),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_purchase_order_items_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], name=op.f('fk_purchase_order_items_purchase_order_id_purchase_orders'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], name=op.f('fk_purchase_order_items_recommendation_id_recommendations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_purchase_order_items')),
    sa.UniqueConstraint('recommendation_id', name=op.f('uq_purchase_order_items_recommendation_id'))
    )
    op.create_index(op.f('ix_purchase_order_items_product_id'), 'purchase_order_items', ['product_id'], unique=False)
    op.create_index(op.f('ix_purchase_order_items_purchase_order_id'), 'purchase_order_items', ['purchase_order_id'], unique=False)
    op.create_table('recommendation_adjustments',
    sa.Column('recommendation_id', sa.Uuid(), nullable=False),
    sa.Column('previous_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('new_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('reason', sa.String(length=2000), nullable=False),
    sa.Column('changed_by', sa.Uuid(), nullable=False),
    sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('new_quantity >= 0', name=op.f('ck_recommendation_adjustments_nonnegative_new_quantity')),
    sa.ForeignKeyConstraint(['changed_by'], ['users.id'], name=op.f('fk_recommendation_adjustments_changed_by_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], name=op.f('fk_recommendation_adjustments_recommendation_id_recommendations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_recommendation_adjustments'))
    )
    op.create_index(op.f('ix_recommendation_adjustments_changed_by'), 'recommendation_adjustments', ['changed_by'], unique=False)
    op.create_index('ix_recommendation_adjustments_recommendation_changed', 'recommendation_adjustments', ['recommendation_id', 'changed_at'], unique=False)


def downgrade() -> None:
    # Reverse dependency order; no CASCADE drops or objects outside this revision.
    op.drop_index('ix_recommendation_adjustments_recommendation_changed', table_name='recommendation_adjustments')
    op.drop_index(op.f('ix_recommendation_adjustments_changed_by'), table_name='recommendation_adjustments')
    op.drop_table('recommendation_adjustments')
    op.drop_index(op.f('ix_purchase_order_items_purchase_order_id'), table_name='purchase_order_items')
    op.drop_index(op.f('ix_purchase_order_items_product_id'), table_name='purchase_order_items')
    op.drop_table('purchase_order_items')
    op.drop_index(op.f('ix_order_exports_purchase_order_id'), table_name='order_exports')
    op.drop_index(op.f('ix_order_exports_created_by'), table_name='order_exports')
    op.drop_table('order_exports')
    op.drop_index(op.f('ix_detected_anomalies_sales_transaction_id'), table_name='detected_anomalies')
    op.drop_index(op.f('ix_detected_anomalies_calculation_run_id'), table_name='detected_anomalies')
    op.drop_table('detected_anomalies')
    op.drop_index('uq_supplier_products_primary_product', table_name='supplier_products', postgresql_where=sa.text('is_active = true AND is_primary = true'), sqlite_where=sa.text('is_active = true AND is_primary = true'))
    op.drop_index('ix_supplier_products_product_id', table_name='supplier_products')
    op.drop_table('supplier_products')
    op.drop_index('ix_stockout_periods_warehouse_id', table_name='stockout_periods')
    op.drop_index('ix_stockout_periods_product_warehouse_period', table_name='stockout_periods')
    op.drop_index('ix_stockout_periods_import_batch_id', table_name='stockout_periods')
    op.drop_table('stockout_periods')
    op.drop_index('ix_seasonality_coefficients_product_id', table_name='seasonality_coefficients')
    op.drop_index('ix_seasonality_coefficients_import_batch_id', table_name='seasonality_coefficients')
    op.drop_index('ix_seasonality_coefficients_category_id', table_name='seasonality_coefficients')
    op.drop_table('seasonality_coefficients')
    op.drop_index('ix_sales_transactions_warehouse_id', table_name='sales_transactions')
    op.drop_index('ix_sales_transactions_product_warehouse_sold', table_name='sales_transactions')
    op.drop_index('ix_sales_transactions_original_transaction_id', table_name='sales_transactions')
    op.drop_index('ix_sales_transactions_customer_sold', table_name='sales_transactions', postgresql_where=sa.text('anonymous_customer_id IS NOT NULL'), sqlite_where=sa.text('anonymous_customer_id IS NOT NULL'))
    op.drop_table('sales_transactions')
    op.drop_index('ix_recommendations_run_warehouse_status', table_name='recommendations')
    op.drop_index('ix_recommendations_run_supplier_urgency', table_name='recommendations')
    op.drop_index('ix_recommendations_run_product_warehouse', table_name='recommendations')
    op.drop_table('recommendations')
    op.drop_index(op.f('ix_purchase_orders_warehouse_id'), table_name='purchase_orders')
    op.drop_index('ix_purchase_orders_supplier_status_created', table_name='purchase_orders')
    op.drop_index(op.f('ix_purchase_orders_created_from_run_id'), table_name='purchase_orders')
    op.drop_index(op.f('ix_purchase_orders_created_by'), table_name='purchase_orders')
    op.drop_index(op.f('ix_purchase_orders_approved_by'), table_name='purchase_orders')
    op.drop_table('purchase_orders')
    op.drop_index('ix_monthly_sales_warehouse_id', table_name='monthly_sales')
    op.drop_index('ix_monthly_sales_product_warehouse_period', table_name='monthly_sales')
    op.drop_table('monthly_sales')
    op.drop_index('ix_material_requirements_warehouse_id', table_name='material_requirements')
    op.drop_index('ix_material_requirements_product_id', table_name='material_requirements')
    op.drop_index('ix_material_requirements_import_batch_id', table_name='material_requirements')
    op.drop_table('material_requirements')
    op.drop_index('ix_inventory_snapshots_warehouse_id', table_name='inventory_snapshots')
    op.drop_index('ix_inventory_snapshots_product_warehouse_snapshot', table_name='inventory_snapshots')
    op.drop_table('inventory_snapshots')
    op.drop_index('ix_in_transit_items_supplier_id', table_name='in_transit_items')
    op.drop_index('ix_in_transit_items_product_warehouse_status_expected', table_name='in_transit_items')
    op.drop_index('ix_in_transit_items_import_batch_id', table_name='in_transit_items')
    op.drop_index('ix_in_transit_items_destination_warehouse_id', table_name='in_transit_items')
    op.drop_table('in_transit_items')
    op.drop_index('ix_growth_assumptions_warehouse_id', table_name='growth_assumptions')
    op.drop_index('ix_growth_assumptions_product_id', table_name='growth_assumptions')
    op.drop_index('ix_growth_assumptions_import_batch_id', table_name='growth_assumptions')
    op.drop_index('ix_growth_assumptions_category_id', table_name='growth_assumptions')
    op.drop_table('growth_assumptions')
    op.drop_index(op.f('ix_demand_forecasts_warehouse_id'), table_name='demand_forecasts')
    op.drop_index(op.f('ix_demand_forecasts_product_id'), table_name='demand_forecasts')
    op.drop_index(op.f('ix_demand_forecasts_calculation_run_id'), table_name='demand_forecasts')
    op.drop_table('demand_forecasts')
    op.drop_index(op.f('ix_calculation_run_imports_import_batch_id'), table_name='calculation_run_imports')
    op.drop_table('calculation_run_imports')
    op.drop_index('ix_products_category_id', table_name='products')
    op.drop_table('products')
    op.drop_index('uq_import_batches_completed_checksum', table_name='import_batches', postgresql_where=sa.text("status = 'completed'"), sqlite_where=sa.text("status = 'completed'"))
    op.drop_index('ix_import_batches_imported_by', table_name='import_batches')
    op.drop_table('import_batches')
    op.drop_index(op.f('ix_calculation_runs_warehouse_id'), table_name='calculation_runs')
    op.drop_index('ix_calculation_runs_status_started_at', table_name='calculation_runs')
    op.drop_index(op.f('ix_calculation_runs_started_by'), table_name='calculation_runs')
    op.drop_index(op.f('ix_calculation_runs_category_id'), table_name='calculation_runs')
    op.drop_table('calculation_runs')
    op.drop_table('warehouses')
    op.drop_table('users')
    op.drop_table('suppliers')
    op.drop_index('ix_categories_parent_id', table_name='categories')
    op.drop_table('categories')
