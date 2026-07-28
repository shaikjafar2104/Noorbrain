from collections import Counter

class HabitAI:

    def analyse(self, habits):

        recent = habits.get("recent", [])

        arrivals = Counter()
        weekdays = Counter()

        durations = []

        for e in recent:

            h = e.get("hour")
            if h is not None:
                arrivals[h] += 1

            w = e.get("weekday")
            if w:
                weekdays[w] += 1

            d = e.get("duration")
            if isinstance(d,(int,float)):
                durations.append(d)

        insights=[]

        if arrivals:
            hour,_ = arrivals.most_common(1)[0]
            insights.append(
                f"Most arrivals happen around {hour}:00"
            )

        if weekdays:
            day,_=weekdays.most_common(1)[0]
            insights.append(
                f"Most active day is {day}"
            )

        if durations:
            avg=sum(durations)/len(durations)
            insights.append(
                f"Average stay {avg:.1f} seconds"
            )

        return {
            "status":"ready",
            "insights":insights
        }

habit_ai=HabitAI()
