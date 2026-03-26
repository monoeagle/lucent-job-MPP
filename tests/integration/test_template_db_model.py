# tests/integration/test_template_db_model.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models.service_template import ServiceTemplateModel


class TestServiceTemplateModel:
    def setup_method(self):
        self.engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)

    def teardown_method(self):
        Base.metadata.drop_all(self.engine)

    def test_create_template(self):
        session = self.Session()
        template = ServiceTemplateModel(
            id=str(uuid.uuid4()),
            slug="vm-linux",
            version="1.0.0",
            type="vm",
            display_name="Linux VM",
            description="A test VM.",
            category="Compute",
            tofu_module_source="git::https://gitlab.internal/tofu/vm.git",
            parameters=[
                {
                    "key": "cpu_cores",
                    "label": "CPU",
                    "type": "integer",
                    "required": True,
                    "tofu_variable_name": "cpu_cores",
                    "display_order": 1,
                    "constraints": {"min": 1, "max": 64},
                }
            ],
            cross_parameter_rules=[],
            status="active",
        )
        session.add(template)
        session.commit()

        loaded = session.query(ServiceTemplateModel).filter_by(slug="vm-linux").first()
        assert loaded is not None
        assert loaded.version == "1.0.0"
        assert loaded.parameters[0]["key"] == "cpu_cores"
        session.close()

    def test_unique_constraint_slug_version(self):
        session = self.Session()
        t1 = ServiceTemplateModel(
            id=str(uuid.uuid4()), slug="vm-linux", version="1.0.0",
            type="vm", display_name="VM 1", category="Compute",
            tofu_module_source="git::https://gitlab.internal/tofu/vm.git",
            parameters=[{"key": "cpu", "label": "CPU", "type": "integer",
                         "required": True, "tofu_variable_name": "cpu",
                         "display_order": 1, "constraints": {}}],
            cross_parameter_rules=[], status="active",
        )
        t2 = ServiceTemplateModel(
            id=str(uuid.uuid4()), slug="vm-linux", version="1.0.0",
            type="vm", display_name="VM 2", category="Compute",
            tofu_module_source="git::https://gitlab.internal/tofu/vm.git",
            parameters=[{"key": "cpu", "label": "CPU", "type": "integer",
                         "required": True, "tofu_variable_name": "cpu",
                         "display_order": 1, "constraints": {}}],
            cross_parameter_rules=[], status="active",
        )
        session.add(t1)
        session.commit()
        session.add(t2)
        from sqlalchemy.exc import IntegrityError
        import pytest
        with pytest.raises(IntegrityError):
            session.commit()
        session.close()
