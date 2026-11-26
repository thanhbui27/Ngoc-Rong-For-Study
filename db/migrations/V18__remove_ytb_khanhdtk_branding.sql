-- Remove old branding from existing databases without deleting game data.
UPDATE item_template
SET description = TRIM(
    REPLACE(
        REPLACE(
            REPLACE(
                REPLACE(
                    REPLACE(description, CONCAT(CHAR(13), CHAR(10), 'YTB KhanhDTK'), ''),
                    'YTB KhanhDTK năm mới', 'Sự kiện năm mới'
                ),
                'YTB KhanhDTK, ', ''
            ),
            'YTB KhanhDTK. ', ''
        ),
        'YTB KhanhDTK', ''
    )
)
WHERE description LIKE '%YTB KhanhDTK%';

UPDATE task_main_template
SET NAME = REPLACE(NAME, 'YTB KhanhDTK', 'Nhiệm vụ đặc biệt'),
    detail = REPLACE(detail, 'YTB KhanhDTK', 'Nhiệm vụ đặc biệt')
WHERE NAME LIKE '%YTB KhanhDTK%'
   OR detail LIKE '%YTB KhanhDTK%';

UPDATE task_sub_template
SET NAME = REPLACE(NAME, 'YTB KhanhDTK', 'Nhiệm vụ đặc biệt'),
    notify = REPLACE(notify, 'YTB KhanhDTK', 'Nhiệm vụ đặc biệt')
WHERE NAME LIKE '%YTB KhanhDTK%'
   OR notify LIKE '%YTB KhanhDTK%';

UPDATE alert
SET content = REPLACE(content, 'YTB KhanhDTK', 'quản trị viên')
WHERE content LIKE '%YTB KhanhDTK%';
