from django.db.models import Field

import uuid

try:
    # psycopg2 needs us to register the uuid type
    import psycopg2
    psycopg2.extras.register_uuid()
except (ImportError, AttributeError):
    pass

class UUIDField(Field):
    """
        A field which stores a UUID value in hex format. This may also have
        the Boolean attribute 'auto' which will set the value on initial save to a
        new UUID value (calculated using the UUID1 method). Note that while all
        UUIDs are expected to be unique we enforce this with a DB constraint.
    """
    # TODO: support UUID types in Postgres
    # TODO: support binary storage types
    # __metaclass__ = models.SubfieldBase

    def __init__(self, version=4, node=None, clock_seq=None, namespace=None, name=None, auto=False, *args, **kwargs):
        assert version in (1, 3, 4, 5), "UUID version %s is not supported." % (version,)
        self.auto = auto
        self.version = version
        # We store UUIDs in hex format, which is fixed at 32 characters.
        kwargs['max_length'] = 32
        if auto:
            # Do not let the user edit UUIDs if they are auto-assigned.
            kwargs['editable'] = False
            kwargs['blank'] = True
            kwargs['unique'] = True
        if version == 1:
            self.node, self.clock_seq = node, clock_seq
        elif version in (3, 5):
            self.namespace, self.name = namespace, name
        super(UUIDField, self).__init__(*args, **kwargs)
        
    def contribute_to_class(self, cls, name):
        if self.primary_key == True: 
            assert not cls._meta.has_auto_field, "A model can't have more than one AutoField: %s %s %s; have %s" % (self, cls, name, cls._meta.auto_field)
            super(UUIDField, self).contribute_to_class(cls, name)
            cls._meta.has_auto_field = True
            cls._meta.auto_field = self
        else:
            super(UUIDField, self).contribute_to_class(cls, name)
            
    def _create_uuid(self):
        if self.version == 1:
            args = (self.node, self.clock_seq)
        elif self.version in (3, 5):
            args = (self.namespace, self.name)
        else:
            args = ()
        return getattr(uuid, 'uuid%s' % (self.version,))(*args)

    def db_type(self, connection=None):
        return 'char(%s)' % (self.max_length,)

    def pre_save(self, model_instance, add):
        """ see CharField.pre_save
            This is used to ensure that we auto-set values if required.
        """
        value = getattr(model_instance, self.attname, None)
        if self.auto and add and not value:
            # Assign a new value for this attribute if required.
            value = self._create_uuid().hex
            setattr(model_instance, self.attname, value)
        return value

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        from south.modelsinspector import introspector
        field_class = "uuidfield.fields.UUIDField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)
