import unittest

from app.domain.entities import Gender, VoiceDesignParams


class VoiceDesignParamsTests(unittest.TestCase):
    def test_custom_instruction_overrides_attributes(self):
        params = VoiceDesignParams(gender=Gender.FEMALE, custom_instruct="warm narrator")
        self.assertEqual(params.to_instruct_string(), "warm narrator")

    def test_attributes_are_serialized_for_omnivoice(self):
        params = VoiceDesignParams(gender=Gender.FEMALE)
        self.assertEqual(params.to_instruct_string(), "female")


if __name__ == "__main__":
    unittest.main()
