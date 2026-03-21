a = input('список:')[1:-1].split(', ')
scores = list(map(int, a))
student_score =int(input('баллы:'))

def check_winners(scores, student_score):
    a = sorted(scores)
    if int(student_score) == a[-3] or int(student_score) == a[-2] or int(student_score) == a[-1]:
        return 'Вы в тройке победителей!'
    else:
        return 'Вы не попали в тройку победителей.'


print(check_winners(scores, student_score))
