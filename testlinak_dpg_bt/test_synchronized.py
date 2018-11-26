#
#
#


import unittest

from linak_dpg_bt.synchronized import synchronized


@synchronized
def mockFunction1(self):
    '''Description'''
    return 1


class ObjectMock():
    
    def __init__(self):
        pass
    
    @synchronized
    def methodA1(self):
        '''Description A1'''
        return 1
    
    @synchronized()
    def methodA2(self):
        '''Description A2'''
        return 2
    
    @synchronized("test_lock")
    def methodA3(self):
        '''Description A3'''
        return 3
    
    @synchronized
    def methodB1(self, arg1):
        '''Description B1'''
        return arg1
    
    @synchronized()
    def methodB2(self, arg1):
        '''Description B2'''
        return arg1
    
    @synchronized("test_lock")
    def methodB3(self, arg1):
        '''Description B3'''
        return arg1
    
    @synchronized
    def static1(self):
        '''Description'''
        return -1


class SynchronizedTest(unittest.TestCase):
    def setUp(self):
        ## Called before testfunction is executed
        pass
  
    def tearDown(self):
        ## Called after testfunction was executed
        pass
    
    def test_synchronized_method_noArgs001(self):
        obj = ObjectMock()
        self.assertEquals( "Description A1", obj.methodA1.__doc__ )
        self.assertEquals( 1, obj.methodA1() )
    
    def test_synchronized_method_noArgs002(self):
        obj = ObjectMock()
        self.assertEquals( "Description A2", obj.methodA2.__doc__ )
        self.assertEquals( 2, obj.methodA2() )
    
    def test_synchronized_method_noArgs003(self):
        obj = ObjectMock()
        self.assertEquals( "Description B1", obj.methodB1.__doc__ )
        self.assertEquals( 3, obj.methodB1(3) )
    
    def test_synchronized_method_noArgs004(self):
        obj = ObjectMock()
        self.assertEquals( "Description B2", obj.methodB2.__doc__ )
        self.assertEquals( 3, obj.methodB2(3) )
    
    
    def test_synchronized_method_args001(self):
        obj = ObjectMock()
        self.assertEquals( "Description A3", obj.methodA3.__doc__ )
        self.assertEquals( 3, obj.methodA3() )
    
    def test_synchronized_method_args002(self):
        obj = ObjectMock()
        self.assertEquals( "Description B3", obj.methodB3.__doc__ )
        self.assertEquals( 4, obj.methodB3(4) )

    
    def test_synchronized_static001(self):
        obj = ObjectMock()
        self.assertEquals( "Description", obj.static1.__doc__ )
        self.assertEquals( -1, obj.static1() )

    
    def test_synchronized_mockFunction1_fail(self):
        self.assertEquals( "Description", mockFunction1.__doc__ )
        self.assertRaises(TypeError, mockFunction1)

