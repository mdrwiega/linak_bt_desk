#
#
#


import unittest

from linak_dpg_bt.linak_service import Service, Characteristic



class ServiceTest(unittest.TestCase):
    def setUp(self):
        ## Called before testfunction is executed
        pass
  
    def tearDown(self):
        ## Called after testfunction was executed
        pass
       
    def test_constructor_lower(self):
        value = Service( Service.DPG.uuid().lower() )
        self.assertEqual( id(Service.DPG), id(value) )
        self.assertEqual( Service.DPG.uuid(), value.uuid() )
        
    def test_constructor_upper(self):
        value = Service( Service.DPG.uuid().upper() )
        self.assertEqual( id(Service.DPG), id(value) )
        self.assertEqual( Service.DPG.uuid(), value.uuid() )
        
        
class CharacteristicTest(unittest.TestCase):
    def setUp(self):
        ## Called before testfunction is executed
        pass
  
    def tearDown(self):
        ## Called after testfunction was executed
        pass
       
    def test_find_lower(self):
        value = Characteristic.find( Characteristic.DPG.uuid().lower() )
        self.assertEqual( id(Characteristic.DPG), id(value) )
        self.assertEqual( Characteristic.DPG.uuid(), value.uuid() )
        self.assertEqual( Characteristic.DPG.handle(), value.handle() )
        
    def test_find_upper(self):
        value = Characteristic.find( Characteristic.DPG.uuid().upper() )
        self.assertEqual( id(Characteristic.DPG), id(value) )
        self.assertEqual( Characteristic.DPG.uuid(), value.uuid() )
        self.assertEqual( Characteristic.DPG.handle(), value.handle() )
        
    def test_find_handle(self):
        value = Characteristic.find( Characteristic.DPG.handle() )
        self.assertEqual( Characteristic.DPG.uuid(), value.uuid() )
        self.assertEqual( Characteristic.DPG.handle(), value.handle() )

    