import unittest
import test_twonbe

def runTests(verbosity=2):
    # Loader
    loader = unittest.TestLoader()

    # Load test suite
    suite = loader.loadTestsFromModule(test_twonbe)
    
    # Run test suite
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)

if __name__ == "__main__":
    runTests()