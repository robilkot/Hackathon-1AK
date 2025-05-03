from StickerValidatorTest import StickerValidatorTest

sv = StickerValidatorTest()

sv.assert_object_valid(obj="test/test_data/object_valid.png",      expect_true=True)
sv.assert_object_valid(obj="test/test_data/object_invalid.png",    expect_true=False)

sv.assert_params_valid(expect_true=True)
p = sv.sv.get_parameters()
p.sticker_rotation = p.sticker_rotation + 1
sv.assert_params_valid(params=p, expect_true=False)