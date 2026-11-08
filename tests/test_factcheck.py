from bot.factcheck import unsupported_facts

SOURCE = "ETH KL Meetup. Met Ahmad from Binance. About 1,200 people came. Panel at 3pm."


def test_supported_draft_has_no_flags():
    draft = "Great night at ETH KL Meetup with 1200 people. I met Ahmad from Binance."
    assert unsupported_facts(draft, SOURCE) == []


def test_invented_name_flagged():
    assert unsupported_facts("I met Ahmad and Sarah from Coinbase.", SOURCE) == ["Sarah", "Coinbase"]


def test_invented_number_flagged():
    assert unsupported_facts("Over 5,000 builders joined.", SOURCE) == ["5,000"]


def test_number_not_matched_inside_bigger_number():
    assert unsupported_facts("Only 200 came.", SOURCE) == ["200"]


def test_sentence_start_and_hashtags_skipped():
    draft = "Honestly a good event.\nLearned a lot. #Web3 #Malaysia"
    assert unsupported_facts(draft, SOURCE) == []


def test_capitalised_word_after_emoji_is_sentence_start():
    assert unsupported_facts("🚀 Huge energy at the panel.", SOURCE) == []


def test_flags_are_unique():
    assert unsupported_facts("I met Sarah. Then I met Sarah again.", SOURCE) == ["Sarah"]
