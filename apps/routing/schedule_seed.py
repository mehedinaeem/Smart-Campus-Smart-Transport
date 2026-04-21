import datetime


SCHEDULE_SEED_DATA = {
    "hero_schedule": {
        "title": "বিশ্ববিদ্যালয় পরিবহন সময়সূচি",
        "summary": "শিক্ষক, কর্মচারী ও শিক্ষার্থীদের জন্য আলাদা সার্ভিস একসাথে সাজানো হয়েছে যাতে হল গেট, হাসপাতাল গেট, ঢাকা ও ক্যাম্পাস রিটার্ন ট্রিপ দ্রুত দেখা যায়।",
        "badge": "আপডেটেড রুট প্ল্যান",
    },
    "schedule_cards": [
        {"label": "মোট সার্ভিস গ্রুপ", "value": "৪টি", "detail": "শিক্ষক, কর্মচারী, শিক্ষার্থী ও ঢাকা সার্ভিস"},
        {"label": "সকালের প্রথম ট্রিপ", "value": "সকাল ৭:০০", "detail": "বিশ্ববিদ্যালয় ক্যাম্পাস থেকে শিক্ষক ও কর্মচারী"},
        {"label": "রাতের শেষ রিটার্ন", "value": "রাত ৮:১৫", "detail": "বিশ্ববিদ্যালয় ক্যাম্পাস থেকে ঢাকা সার্ভিস"},
    ],
    "sections": [
        {
            "title": "সেকশন ১",
            "subtitle": "শিক্ষক ও কর্মচারী সার্ভিস",
            "groups": [
                {
                    "vehicle": "শিক্ষক",
                    "routes": [
                        {
                            "label": "হল গেট থেকে",
                            "times": [
                                {"time": datetime.time(8, 20), "note": "শিক্ষক, কর্মচারী"},
                                {"time": datetime.time(9, 30), "note": "শিক্ষক"},
                                {"time": datetime.time(18, 0), "note": "শিক্ষক, কর্মচারী"},
                                {"time": datetime.time(19, 30), "note": "শিক্ষক, কর্মচারী"},
                            ],
                        },
                        {
                            "label": "বিশ্ববিদ্যালয় ক্যাম্পাস থেকে",
                            "times": [
                                {"time": datetime.time(7, 0), "note": "শিক্ষক, কর্মচারী"},
                                {"time": datetime.time(8, 0), "note": "শিক্ষক, কর্মচারী"},
                                {"time": datetime.time(14, 10), "note": "শিক্ষক"},
                                {"time": datetime.time(16, 10), "note": "শিক্ষক, কর্মচারী"},
                            ],
                        },
                    ],
                },
                {
                    "vehicle": "বড় বাস",
                    "routes": [
                        {"label": "হল গেট থেকে", "times": [{"time": datetime.time(7, 30), "note": "কর্মচারী"}]},
                        {"label": "বিশ্ববিদ্যালয় ক্যাম্পাস থেকে", "times": [{"time": datetime.time(16, 30), "note": "কর্মচারী"}]},
                    ],
                },
            ],
        },
        {
            "title": "সেকশন ২",
            "subtitle": "হাসপাতাল গেট মাইক্রোবাস",
            "groups": [
                {
                    "vehicle": "মাইক্রোবাস",
                    "routes": [
                        {"label": "হাসপাতাল গেট থেকে", "times": [{"time": datetime.time(8, 55), "note": "কর্মচারী"}]},
                        {"label": "বিশ্ববিদ্যালয় ক্যাম্পাস থেকে", "times": [{"time": datetime.time(16, 10), "note": "কর্মচারী"}]},
                    ],
                }
            ],
        },
        {
            "title": "সেকশন ৩",
            "subtitle": "শিক্ষার্থী ও সাপোর্ট বাস সার্ভিস",
            "groups": [
                {
                    "vehicle": "শিক্ষার্থীদের বাস",
                    "routes": [
                        {
                            "label": "ক্যাম্পাস-সংলগ্ন পিকআপ / অফিসমুখী রুট",
                            "times": [
                                {"time": datetime.time(8, 30), "note": ""},
                                {"time": datetime.time(8, 45), "note": ""},
                                {"time": datetime.time(8, 55), "note": ""},
                                {"time": datetime.time(10, 45), "note": ""},
                            ],
                        },
                        {
                            "label": "বিশ্ববিদ্যালয় ক্যাম্পাস থেকে",
                            "times": [
                                {"time": datetime.time(12, 30), "note": ""},
                                {"time": datetime.time(14, 15), "note": ""},
                                {"time": datetime.time(15, 15), "note": ""},
                            ],
                        },
                    ],
                },
                {
                    "vehicle": "অতিরিক্ত সাপোর্ট বাস",
                    "routes": [
                        {
                            "label": "সাপোর্ট সার্ভিস প্রস্থান",
                            "times": [
                                {"time": datetime.time(19, 0), "note": ""},
                                {"time": datetime.time(20, 0), "note": ""},
                            ],
                        },
                        {
                            "label": "বিশ্ববিদ্যালয় ক্যাম্পাস থেকে",
                            "times": [
                                {"time": datetime.time(16, 15), "note": ""},
                                {"time": datetime.time(19, 30), "note": ""},
                            ],
                        },
                    ],
                },
            ],
        },
        {
            "title": "সেকশন ৪",
            "subtitle": "ঢাকা সার্ভিস",
            "groups": [
                {
                    "vehicle": "বড় বাস (ঢাকা সার্ভিস)",
                    "routes": [
                        {
                            "label": "ঢাকা থেকে",
                            "times": [
                                {"time": datetime.time(8, 20), "note": ""},
                                {"time": datetime.time(10, 0), "note": ""},
                            ],
                        },
                        {
                            "label": "বিশ্ববিদ্যালয় ক্যাম্পাস থেকে",
                            "times": [
                                {"time": datetime.time(14, 0), "note": ""},
                                {"time": datetime.time(20, 15), "note": ""},
                            ],
                        },
                    ],
                }
            ],
        },
    ],
}


def seed_bus_payload():
    return [
        {"code": f"BUS-{index:02d}", "label": f"Campus Bus {index}", "seat_capacity": 32, "is_active": True}
        for index in range(1, 13)
    ]
