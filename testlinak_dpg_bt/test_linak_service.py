#
#
#


import unittest

from linak_dpg_bt.linak_service import Characteristic



class CharacteristicTest(unittest.TestCase):
    def setUp(self):
        ## Called before testfunction is executed
        pass
  
    def tearDown(self):
        ## Called after testfunction was executed
        pass
       
    def test_constructor_lower(self):
        value = Characteristic( Characteristic.DPG.value.lower() )
        self.assertEqual( Characteristic.DPG, value )
        
    def test_constructor_upper(self):
        value = Characteristic( Characteristic.DPG.value.upper() )
        self.assertEqual( Characteristic.DPG, value )
    